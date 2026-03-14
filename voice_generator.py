import edge_tts
import asyncio
import os
import re
from config import Config

class VoiceGenerator:
    def __init__(self):
        self.voice = Config.VOICE
        self.rate = Config.VOICE_RATE
    
    def generate_from_script(self, script_data):
        text = script_data.get("script", "")
        text = text.replace(" | ", "। ").replace("|", "। ")
        
        topic = script_data.get("topic", "untitled")
        filename = re.sub(r'[^\w\s-]', '', topic)[:50]
        
        audio_path = os.path.join(Config.AUDIO_DIR, f"{filename}.mp3")
        srt_path = os.path.join(Config.AUDIO_DIR, f"{filename}.srt")
        
        asyncio.run(self._generate(text, audio_path, srt_path))
        return audio_path, srt_path
    
    async def _generate(self, text, audio_path, srt_path):
        communicate = edge_tts.Communicate(text=text, voice=self.voice, rate=self.rate)
        sub = edge_tts.SubMaker()
        
        with open(audio_path, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    sub.add(chunk["offset"], chunk["duration"], chunk["text"])
        
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(sub.generate_srt())
    
    def create_grouped_subtitles(self, srt_path):
        if not os.path.exists(srt_path):
            return []
        
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        subs = []
        for block in content.strip().split('\n\n'):
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                times = lines[1].split(' --> ')
                start = self._to_sec(times[0].strip())
                end = self._to_sec(times[1].strip())
                text = ' '.join(lines[2:])
                subs.append({"start": start, "end": end, "text": text})
        
        # Group words
        grouped = []
        group = []
        for s in subs:
            group.append(s)
            if len(group) >= Config.WORDS_PER_SUBTITLE or s["text"].endswith(("।",".","|")):
                grouped.append({
                    "start": group[0]["start"],
                    "end": group[-1]["end"],
                    "text": " ".join(g["text"] for g in group)
                })
                group = []
        if group:
            grouped.append({
                "start": group[0]["start"],
                "end": group[-1]["end"],
                "text": " ".join(g["text"] for g in group)
            })
        return grouped
    
    def _to_sec(self, t):
        t = t.replace(',', '.')
        p = t.split(':')
        return int(p[0])*3600 + int(p[1])*60 + float(p[2])