import json
import random
import re
import os
import requests
from config import Config

class ScriptGenerator:
    def __init__(self):
        self.niche = Config.CHANNEL_NICHE
        self.topics = Config.TOPICS.get(self.niche, Config.TOPICS["motivation"])
    
    def generate_script(self, custom_topic=None):
        topic = custom_topic or random.choice(self.topics)
        
        prompt = f"""Create a 60-second Hindi video script about: "{topic}"
Return ONLY valid JSON (no markdown, no explanation):
{{"topic":"{topic}","title_hindi":"Hindi title here","title_english":"English title here","script":"वाक्य 1। | वाक्य 2। | वाक्य 3। | वाक्य 4। | वाक्य 5। | वाक्य 6। | वाक्य 7।","hook":"hook line in Hindi","cta":"subscribe करें","mood":"motivational","tags_hindi":["टैग1","टैग2","टैग3"],"tags_english":["tag1","tag2","tag3","tag4","tag5"],"hashtags":["#tag1","#tag2","#tag3","#tag4","#tag5"],"description":"YouTube description in Hindi","caption_facebook":"Facebook caption with emojis"}}"""
        
        # Try multiple free methods
        result = self._try_g4f(prompt, topic)
        if result:
            return result
        
        result = self._try_free_api(prompt, topic)
        if result:
            return result
        
        # Fallback
        return self._fallback_script(topic)
    
    def _try_g4f(self, prompt, topic):
        """Try g4f library"""
        try:
            import g4f
            response = g4f.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a Hindi content writer. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ]
            )
            return self._parse_response(response, topic)
        except Exception as e:
            print(f"g4f failed: {e}")
            return None
    
    def _try_free_api(self, prompt, topic):
        """Try free API alternatives"""
        try:
            # DuckDuckGo AI Chat (free, no API key)
            url = "https://duckduckgo.com/duckchat/v1/chat"
            headers = {
                "Content-Type": "application/json",
                "x-vqd-4": self._get_vqd_token()
            }
            data = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }
            resp = requests.post(url, json=data, headers=headers, timeout=30)
            if resp.status_code == 200:
                text = ""
                for line in resp.text.split('\n'):
                    if line.startswith('data: '):
                        try:
                            chunk = json.loads(line[6:])
                            if chunk.get("message"):
                                text += chunk["message"]
                        except:
                            pass
                return self._parse_response(text, topic)
        except Exception as e:
            print(f"Free API failed: {e}")
        return None
    
    def _get_vqd_token(self):
        """Get DuckDuckGo VQD token"""
        try:
            resp = requests.get(
                "https://duckduckgo.com/duckchat/v1/status",
                headers={"x-vqd-accept": "1"}
            )
            return resp.headers.get("x-vqd-4", "")
        except:
            return ""
    
    def _parse_response(self, response, topic):
        """Parse AI response to JSON"""
        if not response:
            return None
        
        response = str(response).strip()
        
        # Remove markdown code blocks
        if "```" in response:
            response = re.sub(r'```json\s*', '', response)
            response = re.sub(r'```\s*', '', response)
        response = response.strip()
        
        # Find JSON in response
        start = response.find('{')
        end = response.rfind('}')
        if start != -1 and end != -1:
            response = response[start:end+1]
        
        try:
            data = json.loads(response)
            # Validate
            if data.get("script") and data.get("title_hindi"):
                print(f"✅ Script generated: {data['title_hindi']}")
                return data
        except json.JSONDecodeError:
            pass
        
        return None
    
    def _fallback_script(self, topic):
        """Fallback script if all AI fails"""
        scripts = {
            "motivation": {
                "script": "क्या आप भी जिंदगी में हार मान चुके हैं? | रुकिए, ये वीडियो आपके लिए है। | सफलता उन्हीं को मिलती है जो हार नहीं मानते। | हर सुबह एक नया मौका लेकर आती है। | अपने सपनों को कभी मत छोड़ो। | मेहनत कभी बेकार नहीं जाती। | जो लोग आज मेहनत करते हैं कल दुनिया उनका नाम जानती है। | उठो जागो और तब तक मत रुको जब तक लक्ष्य पूरा न हो जाए। | अगर ये वीडियो अच्छी लगी तो लाइक और सब्सक्राइब जरूर करें।",
                "hook": "क्या आप भी जिंदगी में हार मान चुके हैं?"
            },
            "facts": {
                "script": "क्या आप जानते हैं ये हैरान कर देने वाला फैक्ट? | दुनिया में ऐसी बहुत सी बातें हैं जो आपको चौंका देंगी। | आज हम आपको बताएंगे कुछ ऐसे ही रोचक तथ्य। | ये सुनकर आपका दिमाग हिल जाएगा। | विज्ञान ने साबित किया है कि इंसान अपने दिमाग का सिर्फ दस प्रतिशत ही इस्तेमाल करता है। | अगर ऐसे और फैक्ट्स चाहिए तो चैनल को सब्सक्राइब करें।",
                "hook": "क्या आप जानते हैं ये हैरान कर देने वाला फैक्ट?"
            },
            "tech": {
                "script": "आज मैं आपको बताऊंगा एक ऐसी ट्रिक जो आपका फोन स्मार्ट बना देगी। | ये hidden feature बहुत कम लोग जानते हैं। | अपने फोन की सेटिंग्स में जाइए। | ये ऑप्शन ऑन कीजिए और देखिए कमाल। | आपका फोन दोगुना फास्ट चलेगा। | ऐसी और टिप्स के लिए चैनल सब्सक्राइब करें।",
                "hook": "ये hidden feature बहुत कम लोग जानते हैं!"
            },
            "health": {
                "script": "सुबह उठकर ये एक काम करो सेहत बदल जाएगी। | ज्यादातर लोग ये गलती करते हैं। | सुबह खाली पेट गर्म पानी पीना चाहिए। | इससे शरीर के सारे टॉक्सिन बाहर निकल जाते हैं। | रोज़ तीस मिनट एक्सरसाइज़ करो। | ये छोटी आदतें आपकी जिंदगी बदल देंगी। | ऐसे और टिप्स के लिए सब्सक्राइब करें।",
                "hook": "सुबह उठकर ये एक काम करो सेहत बदल जाएगी!"
            },
            "finance": {
                "script": "अमीर बनना है तो ये पांच बातें याद रखो। | पहला नियम बचत करो। | दूसरा नियम निवेश करो। | तीसरा नियम कभी कर्ज मत लो। | चौथा नियम पैसे से पैसा कमाओ। | पांचवा नियम धैर्य रखो। | ये नियम अपनाओगे तो एक दिन जरूर अमीर बनोगे। | सब्सक्राइब करें।",
                "hook": "अमीर बनना है तो ये पांच बातें याद रखो!"
            }
        }
        
        niche_data = scripts.get(self.niche, scripts["motivation"])
        
        return {
            "topic": topic,
            "title_hindi": f"{topic} - जो सुन लिया जिंदगी बदल जाएगी",
            "title_english": f"{topic} - Life Changing Video",
            "script": niche_data["script"],
            "hook": niche_data["hook"],
            "cta": "लाइक और सब्सक्राइब करें",
            "mood": "motivational",
            "tags_hindi": ["मोटिवेशन", "प्रेरणा", "सफलता", "हिंदी"],
            "tags_english": ["motivation", "hindi", "success", "viral",
                           "trending", "shorts", "inspirational"],
            "hashtags": ["#motivation", "#hindi", "#success", 
                        "#viral", "#trending", "#shorts",
                        "#inspirational", "#india", "#facts"],
            "description": f"🔥 {topic} | इस वीडियो में जानिए {topic} के बारे में | Hindi Motivation\n\n#motivation #hindi #viral",
            "caption_facebook": f"🔥 {topic}\n\n💪 ये सुनो और जिंदगी बदल जाएगी!\n\n#motivation #hindi #viral #trending"
        }
    
    def generate_metadata(self, script_data):
        yt = {
            "title": f"{script_data.get('title_hindi', '')} | {script_data.get('title_english', '')}",
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
