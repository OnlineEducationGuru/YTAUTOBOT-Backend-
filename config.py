import os


class Config:
    CHANNEL_NICHE = "motivation"
    CHANNEL_NAME = "Auto Video Bot"
    LANGUAGE = "hi"
    VIDEO_DURATION_SECONDS = 60
    LONG_VIDEO_DURATION = 300
    VIDEO_TYPE = "short"
    VIDEO_WIDTH = 1080
    VIDEO_HEIGHT = 1920
    FPS = 30
    VOICE = "hi-IN-SwaraNeural"
    VOICE_RATE = "+0%"
    VOICE_PITCH = "+0Hz"
    FONT_NAME = "Arial-Bold"
    FONT_SIZE = 45
    FONT_COLOR = "white"
    SUBTITLE_BG_OPACITY = 0.7
    WORDS_PER_SUBTITLE = 6
    
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    OUTPUT_DIR = os.path.join(BASE_DIR, "output")
    SCRIPTS_DIR = os.path.join(OUTPUT_DIR, "scripts")
    AUDIO_DIR = os.path.join(OUTPUT_DIR, "audio")
    VIDEO_DIR = os.path.join(OUTPUT_DIR, "videos")
    THUMBNAIL_DIR = os.path.join(OUTPUT_DIR, "thumbnails")
    TEMP_DIR = os.path.join(OUTPUT_DIR, "temp")
    CREDENTIALS_DIR = os.path.join(BASE_DIR, "credentials")
    
    YOUTUBE_CLIENT_SECRET = os.path.join(CREDENTIALS_DIR, "youtube_client_secret.json")
    YOUTUBE_CATEGORY_ID = "22"
    YOUTUBE_PRIVACY = "public"
    
    FACEBOOK_PAGE_ID = os.environ.get("FACEBOOK_PAGE_ID", "")
    FACEBOOK_ACCESS_TOKEN = os.environ.get("FACEBOOK_ACCESS_TOKEN", "")
    
    TOPICS = {
        "motivation": [
            "सफलता के नियम", "आत्मविश्वास कैसे बढ़ाएं", "सुबह की आदतें",
            "अमीर लोगों की सोच", "जीवन बदलने वाली बातें"
        ],
        "tech": ["AI tools", "smartphone tips", "hidden features"],
        "facts": ["amazing facts", "psychological facts", "science facts"],
        "health": ["weight loss tips", "yoga benefits", "mental health"],
        "finance": ["पैसे कैसे बचाएं", "share market basics", "passive income"],
    }
    
    @classmethod
    def update_from_dict(cls, data):
        """Update config from settings dictionary"""
        if data.get("channel_name"):
            cls.CHANNEL_NAME = data["channel_name"]
        if data.get("channel_niche"):
            cls.CHANNEL_NICHE = data["channel_niche"]
        if data.get("voice"):
            cls.VOICE = data["voice"]
        if data.get("voice_speed"):
            cls.VOICE_RATE = data["voice_speed"]
        if data.get("facebook_page_id"):
            cls.FACEBOOK_PAGE_ID = data["facebook_page_id"]
        if data.get("facebook_token"):
            cls.FACEBOOK_ACCESS_TOKEN = data["facebook_token"]
        if data.get("short_duration"):
            cls.VIDEO_DURATION_SECONDS = data["short_duration"]
        if data.get("long_duration"):
            cls.LONG_VIDEO_DURATION = data["long_duration"] * 60
    
    @classmethod
    def create_directories(cls):
        dirs = [cls.OUTPUT_DIR, cls.SCRIPTS_DIR, cls.AUDIO_DIR,
                cls.VIDEO_DIR, cls.THUMBNAIL_DIR, cls.TEMP_DIR,
                cls.CREDENTIALS_DIR]
        for d in dirs:
            os.makedirs(d, exist_ok=True)


Config.create_directories()