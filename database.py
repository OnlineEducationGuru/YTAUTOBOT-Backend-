"""
Simple JSON-based database (no external DB needed)
"""

import os
import json
from datetime import datetime

DB_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DB_DIR, exist_ok=True)


class Database:
    def __init__(self):
        self.settings_file = os.path.join(DB_DIR, "settings.json")
        self.videos_file = os.path.join(DB_DIR, "videos.json")
        self.uploads_file = os.path.join(DB_DIR, "uploads.json")
        self.analytics_file = os.path.join(DB_DIR, "analytics.json")
    
    def _read(self, filepath, default=None):
        if default is None:
            default = {}
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return default
    
    def _write(self, filepath, data):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    
    # Settings
    def save_settings(self, settings):
        existing = self._read(self.settings_file)
        existing.update(settings)
        self._write(self.settings_file, existing)
    
    def get_settings(self):
        return self._read(self.settings_file)
    
    # Videos
    def save_video(self, video_data):
        videos = self._read(self.videos_file, [])
        videos.insert(0, video_data)
        self._write(self.videos_file, videos)
    
    def get_videos(self):
        return self._read(self.videos_file, [])
    
    def delete_video(self, video_id):
        videos = self._read(self.videos_file, [])
        videos = [v for v in videos if v.get("id") != video_id]
        self._write(self.videos_file, videos)
    
    # Uploads
    def log_upload(self, platform, title, result):
        uploads = self._read(self.uploads_file, [])
        uploads.insert(0, {
            "platform": platform,
            "title": title,
            "result": str(result),
            "time": datetime.now().isoformat()
        })
        self._write(self.uploads_file, uploads)
    
    # Analytics
    def get_analytics(self):
        videos = self._read(self.videos_file, [])
        uploads = self._read(self.uploads_file, [])
        
        yt_uploads = [u for u in uploads if u.get("platform") == "youtube"]
        fb_uploads = [u for u in uploads if u.get("platform") == "facebook"]
        
        return {
            "total_videos": len(videos),
            "youtube_uploads": len(yt_uploads),
            "facebook_uploads": len(fb_uploads),
            "uploaded": len(uploads),
            "failed": 0,
            "scheduled": 0
        }