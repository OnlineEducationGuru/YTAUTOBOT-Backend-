import os
import re
import random
import numpy as np
from PIL import Image, ImageDraw
from moviepy.editor import (AudioFileClip, ColorClip, CompositeVideoClip, TextClip, ImageClip)
from config import Config
from voice_generator import VoiceGenerator

class VideoCreator:
    def __init__(self):
        self.width = Config.VIDEO_WIDTH
        self.height = Config.VIDEO_HEIGHT
        self.fps = Config.FPS
        self.voice_gen = VoiceGenerator()
        self.themes = [
            {"bg": (10,10,30), "accent": (255,215,0)},
            {"bg": (20,0,0), "accent": (255,69,0)},
            {"bg": (0,0,0), "accent": (0,191,255)},
            {"bg": (30,0,30), "accent": (186,85,211)},
        ]
    
    def create_video(self, script_data, audio_path, srt_path):
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        theme = random.choice(self.themes)
        
        bg = ColorClip(size=(self.width, self.height), color=theme["bg"], duration=duration)
        
        subs = self.voice_gen.create_grouped_subtitles(srt_path)
        sub_clips = self._make_subs(subs, theme)
        
        clips = [bg] + sub_clips
        video = CompositeVideoClip(clips, size=(self.width, self.height))
        video = video.set_audio(audio).set_duration(duration)
        
        topic = script_data.get("topic", "video")
        filename = re.sub(r'[^\w\s-]', '', topic)[:50]
        out = os.path.join(Config.VIDEO_DIR, f"{filename}.mp4")
        
        video.write_videofile(out, fps=self.fps, codec='libx264',
                            audio_codec='aac', bitrate='3000k',
                            preset='ultrafast', threads=2, logger=None)
        audio.close()
        video.close()
        return out
    
    def _make_subs(self, subs, theme):
        clips = []
        for s in subs:
            text = s["text"].strip()
            if not text or s["end"] - s["start"] <= 0:
                continue
            try:
                txt = TextClip(text, fontsize=Config.FONT_SIZE, color="white",
                             font=Config.FONT_NAME, method='caption',
                             size=(self.width-100, None), align='center',
                             stroke_color='black', stroke_width=2)
                txt = txt.set_position(('center', self.height-400))
                txt = txt.set_start(s["start"]).set_duration(s["end"]-s["start"])
                clips.append(txt)
            except:
                continue
        return clips