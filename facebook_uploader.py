import os
import requests
from config import Config

class FacebookUploader:
    def __init__(self):
        self.page_id = Config.FACEBOOK_PAGE_ID or os.environ.get("FACEBOOK_PAGE_ID", "")
        self.token = Config.FACEBOOK_ACCESS_TOKEN or os.environ.get("FACEBOOK_ACCESS_TOKEN", "")
    
    def upload_video(self, path, caption="", hashtags=""):
        if not self.page_id or not self.token:
            return {"error": "Facebook not configured"}
        
        url = f"https://graph.facebook.com/v18.0/{self.page_id}/videos"
        with open(path, 'rb') as f:
            r = requests.post(url, files={'source': f},
                            data={'description': f"{caption}\n{hashtags}",
                                  'access_token': self.token}, timeout=300)
        result = r.json()
        return {"video_id": result.get("id"), "success": "id" in result}
    
    def upload_reel(self, path, caption=""):
        return self.upload_video(path, caption)
    
    def get_page_insights(self):
        if not self.page_id or not self.token:
            return None
        try:
            r = requests.get(f"https://graph.facebook.com/v18.0/{self.page_id}",
                           params={"fields":"name,followers_count","access_token":self.token})
            return r.json()
        except:
            return None