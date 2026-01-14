import edge_tts
import asyncio
import numpy as np
import sounddevice as sd
import soundfile as sf
from threading import Thread, Event, Lock
from queue import Queue, Empty
import tempfile
import os
import speech_recognition as sr
import io


class AudioHandler:
    def __init__(self):
        self.sound_queue = Queue()
        self.running = True
        self._speech_complete = Event()
        self._speech_complete.set()
        self.voice = "pl-PL-ZofiaNeural"
        self._loop = None
        self._loop_thread = Thread(target=self._start_event_loop, daemon=True)
        self._loop_thread.start()
        self._cache = {}
        self._cache_lock = Lock()
        self.thread = Thread(target=self._process_queue, daemon=True)
        self.thread.start()
    
    def _start_event_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()
    
    def _process_queue(self):
        while self.running:
            try:
                item = self.sound_queue.get(timeout=0.1)
                sound_type = item['type']
                
                if sound_type == 'beep':
                    self._play_beep()
                elif sound_type == 'speech':
                    self._speak_text(item['text'])
                
                self.sound_queue.task_done()
                
                if self.sound_queue.empty():
                    self._speech_complete.set()
                    
            except Empty:
                continue
            except Exception as e:
                print(f"Audio queue error: {e}")
                continue
    
    def _play_beep(self):
        duration = 0.2
        frequency = 880
        sample_rate = 44100
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        wave = np.sin(frequency * 2 * np.pi * t)
        
        envelope = np.exp(-t * 15)
        wave = wave * envelope * 0.6
        
        sd.play(wave, sample_rate)
        sd.wait()
    
    def _speak_text(self, text):
        with self._cache_lock:
            cached = self._cache.get(text)
        
        if cached:
            data, samplerate = cached
            sd.play(data, samplerate)
            sd.wait()
            return
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        temp_path = temp_file.name
        temp_file.close()
        
        try:
            future = asyncio.run_coroutine_threadsafe(
                self._generate_speech(text, temp_path),
                self._loop
            )
            future.result(timeout=10)
            
            data, samplerate = sf.read(temp_path)
            
            with self._cache_lock:
                self._cache[text] = (data.copy(), samplerate)
            
            sd.play(data, samplerate)
            sd.wait()
        except Exception as e:
            print(f"Speech error: {e}")
        finally:
            try:
                os.unlink(temp_path)
            except Exception:
                pass
    
    async def _generate_speech(self, text, output_file):
        communicate = edge_tts.Communicate(text, self.voice)
        await communicate.save(output_file)
    
    def preload_speech(self, texts):
        def preload():
            for text in texts:
                with self._cache_lock:
                    if text in self._cache:
                        continue
                
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                temp_path = temp_file.name
                temp_file.close()
                
                try:
                    future = asyncio.run_coroutine_threadsafe(
                        self._generate_speech(text, temp_path),
                        self._loop
                    )
                    future.result(timeout=10)
                    
                    data, samplerate = sf.read(temp_path)
                    
                    with self._cache_lock:
                        self._cache[text] = (data.copy(), samplerate)
                except Exception as e:
                    print(f"Preload error for '{text}': {e}")
                finally:
                    try:
                        os.unlink(temp_path)
                    except Exception:
                        pass
        
        Thread(target=preload, daemon=True).start()
    
    def queue_beep(self):
        self.sound_queue.put({'type': 'beep'})
    
    def queue_speech(self, text):
        self._speech_complete.clear()
        self.sound_queue.put({'type': 'speech', 'text': text})
    
    def clear_queue(self):
        while not self.sound_queue.empty():
            try:
                self.sound_queue.get_nowait()
            except Exception:
                break
        self._speech_complete.set()
    
    def queue_speech_priority(self, text):
        self.clear_queue()
        self._speech_complete.clear()
        self.sound_queue.put({'type': 'speech', 'text': text})
    
    def wait_for_speech(self, timeout=None):
        self._speech_complete.wait(timeout=timeout)
    
    def stop(self):
        self.running = False
        self.clear_queue()
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)


def listen_for_voice_commands(audio_handler, stop_event, analyzing_event):
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 0.5
    
    mic = sr.Microphone()
    
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)
    
    start_keywords = ['zacznij', 'zaczynaj', 'zaczyna', 'rozpocznij', 'zaczynam']
    stop_keywords = ['pauza', 'pauzuj', 'wstrzymaj', 'przerwa']
    
    while not stop_event.is_set():
        try:
            with mic as source:
                audio = recognizer.listen(source, timeout=2, phrase_time_limit=4)
            
            try:
                text = recognizer.recognize_google(audio, language="pl-PL").lower()
            except sr.UnknownValueError:
                continue
            
            if not analyzing_event.is_set():
                if any(kw in text for kw in start_keywords):
                    audio_handler.queue_speech("Zaczynam")
                    analyzing_event.set()
            else:
                if any(kw in text for kw in stop_keywords):
                    audio_handler.queue_speech("Pauza")
                    analyzing_event.clear()
                
        except sr.WaitTimeoutError:
            continue
        except Exception as e:
            print(f"Speech recognition error: {e}")
            continue