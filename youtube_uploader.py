import os
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from config import Config

class YouTubeUploader:
    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
    
    def __init__(self):
        self.youtube = None
        self.credentials = None
        self._auth()
    
    def _auth(self):
        token_path = os.path.join(Config.CREDENTIALS_DIR, "yt_token.pickle")
        if os.path.exists(token_path):
            with open(token_path, 'rb') as f:
                self.credentials = pickle.load(f)
        
        if not self.credentials or not self.credentials.valid:
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                self.credentials.refresh(Request())
                with open(token_path, 'wb') as f:
                    pickle.dump(self.credentials, f)
            else:
                if not os.path.exists(Config.YOUTUBE_CLIENT_SECRET):
                    return
                return
        
        self.youtube = build('youtube', 'v3', credentials=self.credentials)
    
    def upload_video(self, path, meta):
        if not self.youtube:
            return {"error": "Not authenticated"}
        
        body = {
            "snippet": {
                "title": meta.get("title", "")[:100],
                "description": meta.get("description", "")[:5000],
                "tags": meta.get("tags", [])[:30],
                "categoryId": meta.get("category_id", "22")
            },
            "status": {"privacyStatus": meta.get("privacy", "public")}
        }
        
        media = MediaFileUpload(path, mimetype='video/mp4', resumable=True)
        
        req = self.youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        response = None
        while response is None:
            _, response = req.next_chunk()
        
        return {"video_id": response['id'], "url": f"https://youtube.com/watch?v={response['id']}"}
    
    def get_channel_analytics(self):
        if not self.youtube: return None
        try:
            r = self.youtube.channels().list(part="statistics", mine=True).execute()
            return r["items"][0]["statistics"] if r["items"] else None
        except:
            return None