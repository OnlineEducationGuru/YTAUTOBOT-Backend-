import g4f
import json
import random
import re
import os
from config import Config

class ScriptGenerator:
    def __init__(self):
        self.niche = Config.CHANNEL_NICHE
        self.topics = Config.TOPICS.get(self.niche, Config.TOPICS["motivation"])
    
    def generate_script(self, custom_topic=None):
        topic = custom_topic or random.choice(self.topics)
        
        prompt = f"""Create a 60-second Hindi video script about: "{topic}"
Return ONLY valid JSON:
{{"topic":"{topic}","title_hindi":"Hindi title","title_english":"English title","script":"वाक्य 1। | वाक्य 2। | वाक्य 3।","hook":"hook line","cta":"subscribe करें","mood":"motivational","tags_hindi":["टैग1","टैग2"],"tags_english":["tag1","tag2","tag3","tag4","tag5"],"hashtags":["#tag1","#tag2","#tag3","#tag4","#tag5"],"description":"YouTube description","caption_facebook":"Facebook caption"}}"""
        
        try:
            response = g4f.ChatCompletion.create(
                model=g4f.models.gpt_4,
                messages=[{"role":"user","content":prompt}]
            )
            response = response.strip()
            if response.startswith("```"):
                response = re.sub(r'^```\w*\n?', '', response)
                response = re.sub(r'\n?```$', '', response)
            return json.loads(response.strip())
        except:
            return {
                "topic": topic,
                "title_hindi": f"{topic} - जो सुन लिया जिंदगी बदल जाएगी",
                "title_english": f"{topic} - Life Changing",
                "script": "क्या आप भी जिंदगी में हार मान चुके हैं? | रुकिए, ये वीडियो आपके लिए है। | सफलता उन्हीं को मिलती है जो हार नहीं मानते। | हर सुबह एक नया मौका है। | मेहनत कभी बेकार नहीं जाती। | उठो और तब तक मत रुको जब तक लक्ष्य पूरा न हो। | लाइक और सब्सक्राइब जरूर करें।",
                "hook": "क्या आप भी हार मान चुके हैं?",
                "cta": "लाइक और सब्सक्राइब करें",
                "mood": "motivational",
                "tags_hindi": ["मोटिवेशन", "प्रेरणा", "सफलता"],
                "tags_english": ["motivation", "hindi", "success", "viral", "trending"],
                "hashtags": ["#motivation", "#hindi", "#viral", "#trending", "#shorts"],
                "description": f"{topic} | Hindi Motivation",
                "caption_facebook": f"🔥 {topic}\n💪 #motivation #hindi #viral"
            }
    
    def generate_metadata(self, script_data):
        yt = {
            "title": f"{script_data.get('title_hindi','')} | {script_data.get('title_english','')}",
            "description": script_data.get("description", ""),
            "tags": script_data.get("tags_english", []) + script_data.get("tags_hindi", []),
            "category_id": Config.YOUTUBE_CATEGORY_ID,
            "privacy": Config.YOUTUBE_PRIVACY
        }
        fb = {
            "caption": script_data.get("caption_facebook", ""),
            "hashtags": " ".join(script_data.get("hashtags", []))
        }
        return yt, fb