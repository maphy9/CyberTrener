import edge_tts
import asyncio
import numpy as np
import sounddevice as sd
import soundfile as sf
from threading import Thread, Event
from queue import Queue
import tempfile
import os
import speech_recognition as sr


class AudioHandler:
    def __init__(self):
        self.sound_queue = Queue()
        self.stop_event = Event()
        self.queue_not_empty = Event()
        self.thread = Thread(target=self._process_queue, daemon=True)
        self.thread.start()
        self.voice = "pl-PL-ZofiaNeural"
    
    def _process_queue(self):
        while not self.stop_event.is_set():
            self.queue_not_empty.wait(timeout=0.5)
            
            if self.stop_event.is_set():
                break
            
            if not self.sound_queue.empty():
                sound = self.sound_queue.get()
                
                if sound['type'] == 'beep':
                    self._play_beep()
                elif sound['type'] == 'speech':
                    self._speak_text(sound['text'])
                
                self.sound_queue.task_done()
            else:
                self.queue_not_empty.clear()
    
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
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        temp_path = temp_file.name
        temp_file.close()
        
        try:
            asyncio.run(self._generate_speech(text, temp_path))
            
            data, samplerate = sf.read(temp_path) # type: ignore
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
    
    def queue_beep(self):
        self.sound_queue.put({'type': 'beep'})
        self.queue_not_empty.set()
    
    def queue_speech(self, text):
        self.sound_queue.put({'type': 'speech', 'text': text})
        self.queue_not_empty.set()
    
    def stop(self):
        self.stop_event.set()
        self.queue_not_empty.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)
        
        while not self.sound_queue.empty():
            try:
                self.sound_queue.get_nowait()
            except Exception:
                break


def listen_for_voice_commands(audio_handler, stop_event, analyzing_event):
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 0.5
    
    mic = sr.Microphone()
    
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)
    
    start_keywords = ['start', 'stars', 'stark', 'sztart', 'tart', 'art', 'zacznij', 'zaczynaj', 'rozpocznij', 'dalej', 'gotowy', 'gotowe']
    stop_keywords = ['stop', 'stok', 'top', 'zatrzymaj', 'koniec', 'kończymy', 'pauza', 'czekaj']
    
    while not stop_event.is_set():
        try:
            with mic as source:
                audio = recognizer.listen(source, timeout=2, phrase_time_limit=4)
            
            try:
                text = recognizer.recognize_google(audio, language="pl-PL").lower() # type: ignore
            except sr.UnknownValueError:
                continue
            
            if not analyzing_event.is_set():
                if any(kw in text for kw in start_keywords):
                    audio_handler.queue_speech("Rozpoczynam")
                    analyzing_event.set()
            else:
                if any(kw in text for kw in stop_keywords):
                    audio_handler.queue_speech("Zatrzymuję")
                    analyzing_event.clear()
                
        except sr.WaitTimeoutError:
            continue
        except Exception as e:
            print(f"Speech recognition error: {e}")
            continue