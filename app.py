"""
🎬 Auto Video Bot - Backend API Server
Runs on Render.com (FREE) - 24/7
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import uuid
import threading
import time
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

from config import Config
from script_generator import ScriptGenerator
from voice_generator import VoiceGenerator
from video_creator import VideoCreator
from youtube_uploader import YouTubeUploader
from facebook_uploader import FacebookUploader
from database import Database

app = Flask(__name__)
CORS(app)  # Allow frontend to connect

# Initialize components
db = Database()
scheduler = BackgroundScheduler()
scheduler.start()

# Global state
bot_state = {
    "running": False,
    "auto_mode": False,
    "latest_log": "",
    "tasks": {}
}


# ==================== HEALTH CHECK ====================
@app.route('/api/ping', methods=['GET'])
def ping():
    return jsonify({
        "status": "ok",
        "message": "Auto Video Bot Backend is running! 🤖",
        "time": datetime.now().isoformat(),
        "bot_running": bot_state["running"],
        "auto_mode": bot_state["auto_mode"]
    })


# ==================== SETTINGS ====================
@app.route('/api/settings', methods=['GET'])
def get_settings():
    settings = db.get_settings()
    return jsonify(settings)


@app.route('/api/settings', methods=['POST'])
def save_settings():
    data = request.json
    db.save_settings(data)
    
    # Update config
    Config.update_from_dict(data)
    
    return jsonify({"success": True, "message": "Settings saved!"})


# ==================== VIDEO GENERATION ====================
@app.route('/api/generate', methods=['POST'])
def generate_video():
    """Start video generation (async)"""
    data = request.json or {}
    
    task_id = str(uuid.uuid4())[:8]
    
    # Start generation in background thread
    thread = threading.Thread(
        target=run_generation_pipeline,
        args=(task_id, data)
    )
    thread.daemon = True
    thread.start()
    
    bot_state["tasks"][task_id] = {
        "status": "started",
        "step": 1,
        "message": "Starting generation...",
        "created": datetime.now().isoformat()
    }
    
    return jsonify({
        "task_id": task_id,
        "status": "started",
        "message": "Video generation started!"
    })


@app.route('/api/generate/status/<task_id>', methods=['GET'])
def generation_status(task_id):
    """Check generation progress"""
    task = bot_state["tasks"].get(task_id, {})
    return jsonify(task)


def run_generation_pipeline(task_id, options):
    """Background pipeline - generates video"""
    try:
        settings = db.get_settings()
        
        # Merge options with saved settings
        config = {**settings, **options}
        Config.update_from_dict(config)
        
        # Step 1: Generate Script
        update_task(task_id, 1, "active", "Generating AI script...")
        
        script_gen = ScriptGenerator()
        topic = options.get("topic")
        script_data = script_gen.generate_script(custom_topic=topic)
        
        if not script_data:
            update_task(task_id, 1, "failed", "Script generation failed")
            return
        
        update_task(task_id, 1, "done", "Script generated!")
        
        # Step 2: Generate Voice
        update_task(task_id, 2, "active", "Creating voice over...")
        
        voice_gen = VoiceGenerator()
        audio_path, subtitle_path = voice_gen.generate_from_script(script_data)
        
        update_task(task_id, 2, "done", "Voice over created!")
        
        # Step 3: Create Video
        update_task(task_id, 3, "active", "Rendering video...")
        
        video_type = options.get("video_type", "short")
        
        videos_created = []
        
        if video_type in ["short", "both"]:
            Config.VIDEO_TYPE = "short"
            Config.VIDEO_WIDTH = 1080
            Config.VIDEO_HEIGHT = 1920
            
            creator = VideoCreator()
            video_path = creator.create_video(script_data, audio_path, subtitle_path)
            videos_created.append({"path": video_path, "type": "short"})
        
        if video_type in ["long", "both"]:
            Config.VIDEO_TYPE = "long"
            Config.VIDEO_WIDTH = 1920
            Config.VIDEO_HEIGHT = 1080
            
            # Generate longer script for long video
            if video_type == "both":
                long_script = script_gen.generate_script(custom_topic=topic)
                long_audio, long_srt = voice_gen.generate_from_script(long_script)
            else:
                long_script = script_data
                long_audio, long_srt = audio_path, subtitle_path
            
            creator = VideoCreator()
            video_path = creator.create_video(long_script, long_audio, long_srt)
            videos_created.append({"path": video_path, "type": "long"})
        
        update_task(task_id, 3, "done", "Video rendered!")
        
        # Step 4: Generate Metadata
        update_task(task_id, 4, "active", "Generating metadata...")
        
        yt_meta, fb_meta = script_gen.generate_metadata(script_data)
        
        update_task(task_id, 4, "done", "Metadata generated!")
        
        # Step 5: Upload / Schedule
        update_task(task_id, 5, "active", "Scheduling upload...")
        
        upload_results = {}
        auto_upload = options.get("auto_upload", True)
        
        if auto_upload:
            # Determine if we should upload now or schedule
            from scheduler_service import get_next_peak_time
            
            yt_time = get_next_peak_time("youtube")
            fb_time = get_next_peak_time("facebook")
            
            now = datetime.now()
            
            for video_info in videos_created:
                vid_path = video_info["path"]
                vid_type = video_info["type"]
                
                # YouTube Upload
                if config.get("upload_youtube", True):
                    time_diff = (yt_time - now).total_seconds()
                    
                    if time_diff <= 1800:  # Within 30 min
                        try:
                            yt = YouTubeUploader()
                            meta = yt_meta.copy()
                            if vid_type == "short":
                                meta["title"] = meta["title"] + " #shorts"
                            result = yt.upload_video(vid_path, meta)
                            upload_results["youtube"] = result
                        except Exception as e:
                            upload_results["youtube_error"] = str(e)
                    else:
                        # Schedule for later
                        scheduler.add_job(
                            upload_to_youtube_job,
                            'date',
                            run_date=yt_time,
                            args=[vid_path, yt_meta, vid_type]
                        )
                        upload_results["youtube_scheduled"] = yt_time.isoformat()
                
                # Facebook Upload
                if config.get("upload_facebook", True) and config.get("facebook_page_id"):
                    fb_time_diff = (fb_time - now).total_seconds()
                    
                    if fb_time_diff <= 1800:
                        try:
                            fb = FacebookUploader()
                            caption = fb_meta.get("caption", "")
                            hashtags = fb_meta.get("hashtags", "")
                            
                            if vid_type == "short":
                                result = fb.upload_reel(vid_path, f"{caption}\n{hashtags}")
                            else:
                                result = fb.upload_video(vid_path, caption, hashtags)
                            upload_results["facebook"] = result
                        except Exception as e:
                            upload_results["facebook_error"] = str(e)
                    else:
                        scheduler.add_job(
                            upload_to_facebook_job,
                            'date',
                            run_date=fb_time,
                            args=[vid_path, fb_meta, vid_type]
                        )
                        upload_results["facebook_scheduled"] = fb_time.isoformat()
        
        update_task(task_id, 5, "done", "Complete!")
        
        # Save to database
        video_record = {
            "id": task_id,
            "title": script_data.get("title_hindi", ""),
            "title_en": script_data.get("title_english", ""),
            "topic": script_data.get("topic", ""),
            "video_type": options.get("video_type", "short"),
            "tags": script_data.get("tags_english", []),
            "hashtags": script_data.get("hashtags", []),
            "videos": videos_created,
            "upload_results": upload_results,
            "created": datetime.now().isoformat(),
            "status": "completed"
        }
        
        db.save_video(video_record)
        
        # Update task with final result
        bot_state["tasks"][task_id] = {
            "status": "completed",
            "step": 5,
            "message": "Video generated and scheduled!",
            "title": script_data.get("title_hindi", ""),
            "video_type": options.get("video_type", "short"),
            "tags": script_data.get("tags_english", [])[:10],
            "hashtags": script_data.get("hashtags", [])[:5],
            "youtube_url": upload_results.get("youtube", {}).get("url", ""),
            "scheduled": upload_results.get("youtube_scheduled", 
                        upload_results.get("facebook_scheduled", "")),
        }
        
        bot_state["latest_log"] = f"✅ Video generated: {script_data.get('title_hindi', '')}"
        
    except Exception as e:
        bot_state["tasks"][task_id] = {
            "status": "failed",
            "step": bot_state["tasks"].get(task_id, {}).get("step", 1),
            "message": f"Error: {str(e)}",
            "error": str(e)
        }
        bot_state["latest_log"] = f"❌ Generation failed: {str(e)}"


def update_task(task_id, step, status, message):
    """Update task progress"""
    bot_state["tasks"][task_id] = {
        "status": "processing" if status != "failed" else "failed",
        "step": step,
        "step_status": status,
        "message": message
    }


# ==================== UPLOAD JOBS ====================
def upload_to_youtube_job(video_path, metadata, video_type):
    """Scheduled YouTube upload job"""
    try:
        yt = YouTubeUploader()
        if video_type == "short":
            metadata["title"] = metadata["title"] + " #shorts"
        result = yt.upload_video(video_path, metadata)
        bot_state["latest_log"] = f"✅ YouTube upload complete: {metadata.get('title', '')}"
        db.log_upload("youtube", metadata.get("title", ""), result)
    except Exception as e:
        bot_state["latest_log"] = f"❌ YouTube upload failed: {e}"


def upload_to_facebook_job(video_path, metadata, video_type):
    """Scheduled Facebook upload job"""
    try:
        fb = FacebookUploader()
        caption = metadata.get("caption", "")
        hashtags = metadata.get("hashtags", "")
        
        if video_type == "short":
            result = fb.upload_reel(video_path, f"{caption}\n{hashtags}")
        else:
            result = fb.upload_video(video_path, caption, hashtags)
        
        bot_state["latest_log"] = f"✅ Facebook upload complete"
        db.log_upload("facebook", caption[:50], result)
    except Exception as e:
        bot_state["latest_log"] = f"❌ Facebook upload failed: {e}"


# ==================== VIDEOS ====================
@app.route('/api/videos', methods=['GET'])
def get_videos():
    videos = db.get_videos()
    return jsonify({"videos": videos})


@app.route('/api/videos/<video_id>', methods=['DELETE'])
def delete_video(video_id):
    db.delete_video(video_id)
    return jsonify({"success": True})


# ==================== BOT CONTROL ====================
@app.route('/api/bot/start', methods=['POST'])
def start_bot():
    bot_state["running"] = True
    bot_state["latest_log"] = "🤖 Bot started!"
    return jsonify({"success": True, "message": "Bot started!"})


@app.route('/api/bot/stop', methods=['POST'])
def stop_bot():
    bot_state["running"] = False
    bot_state["auto_mode"] = False
    bot_state["latest_log"] = "⏹️ Bot stopped"
    return jsonify({"success": True, "message": "Bot stopped!"})


@app.route('/api/bot/status', methods=['GET'])
def bot_status():
    return jsonify({
        "running": bot_state["running"],
        "auto_mode": bot_state["auto_mode"],
        "latest_log": bot_state["latest_log"],
        "scheduled_jobs": len(scheduler.get_jobs())
    })


# ==================== AUTO MODE ====================
@app.route('/api/auto/start', methods=['POST'])
def start_auto_mode():
    data = request.json or {}
    
    bot_state["auto_mode"] = True
    bot_state["running"] = True
    
    videos_per_day = data.get("videos_per_day", 1)
    make_shorts = data.get("make_shorts", True)
    make_long = data.get("make_long", False)
    
    # Save auto config
    db.save_settings({**data, "auto_mode": True})
    
    # Schedule daily video generation
    # Generate at different times of day
    generation_hours = [6, 10, 14]  # 6 AM, 10 AM, 2 PM
    
    for i in range(min(videos_per_day, 3)):
        hour = generation_hours[i]
        
        video_type = "both" if (make_shorts and make_long) else ("short" if make_shorts else "long")
        
        job_id = f"auto_gen_{i}"
        
        # Remove existing job if any
        existing = scheduler.get_job(job_id)
        if existing:
            scheduler.remove_job(job_id)
        
        scheduler.add_job(
            auto_generate_job,
            'cron',
            hour=hour,
            minute=0,
            args=[data, video_type],
            id=job_id,
            replace_existing=True
        )
    
    bot_state["latest_log"] = f"🤖 Auto mode started! {videos_per_day} video(s)/day"
    
    # Generate first video immediately
    threading.Thread(
        target=auto_generate_job,
        args=[data, "short" if make_shorts else "long"],
        daemon=True
    ).start()
    
    return jsonify({
        "success": True,
        "message": f"Auto mode started! Will generate {videos_per_day} video(s) per day"
    })


@app.route('/api/auto/stop', methods=['POST'])
def stop_auto_mode():
    bot_state["auto_mode"] = False
    
    # Remove scheduled jobs
    for job in scheduler.get_jobs():
        if job.id.startswith("auto_"):
            scheduler.remove_job(job.id)
    
    bot_state["latest_log"] = "⏹️ Auto mode stopped"
    
    return jsonify({"success": True, "message": "Auto mode stopped"})


def auto_generate_job(config, video_type):
    """Auto generation job - called by scheduler"""
    task_id = f"auto_{str(uuid.uuid4())[:6]}"
    
    options = {
        **config,
        "video_type": video_type,
        "auto_upload": True,
        "topic": None  # AI picks topic
    }
    
    bot_state["latest_log"] = f"🎬 Auto generating video ({video_type})..."
    run_generation_pipeline(task_id, options)


# ==================== ANALYTICS ====================
@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    stats = db.get_analytics()
    return jsonify(stats)


# ==================== SCHEDULE ====================
@app.route('/api/schedule', methods=['GET'])
def get_schedule():
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "next_run": str(job.next_run_time),
            "name": job.name
        })
    return jsonify({"jobs": jobs})


# ==================== AUTH ====================
@app.route('/api/auth/youtube/url', methods=['GET'])
def youtube_auth_url():
    """Get YouTube OAuth URL"""
    try:
        from google_auth_oauthlib.flow import Flow
        
        flow = Flow.from_client_secrets_file(
            Config.YOUTUBE_CLIENT_SECRET,
            scopes=["https://www.googleapis.com/auth/youtube.upload"],
            redirect_uri=request.host_url + "api/auth/youtube/callback"
        )
        
        auth_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        
        return jsonify({"auth_url": auth_url, "state": state})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/api/auth/youtube/callback')
def youtube_auth_callback():
    """YouTube OAuth callback"""
    try:
        from google_auth_oauthlib.flow import Flow
        import pickle
        
        flow = Flow.from_client_secrets_file(
            Config.YOUTUBE_CLIENT_SECRET,
            scopes=["https://www.googleapis.com/auth/youtube.upload"],
            redirect_uri=request.base_url
        )
        
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        
        token_path = os.path.join(Config.CREDENTIALS_DIR, "youtube_token.pickle")
        with open(token_path, 'wb') as f:
            pickle.dump(credentials, f)
        
        return "<h1>✅ YouTube Connected Successfully!</h1><p>You can close this window.</p>"
    except Exception as e:
        return f"<h1>❌ Error: {e}</h1>", 400


# ==================== TEST CONNECTIONS ====================
@app.route('/api/test/connections', methods=['GET'])
def test_connections():
    results = {"youtube": False, "facebook": False}
    
    try:
        yt = YouTubeUploader()
        if yt.youtube:
            yt.get_channel_analytics()
            results["youtube"] = True
    except:
        pass
    
    try:
        fb = FacebookUploader()
        info = fb.get_page_insights()
        if info:
            results["facebook"] = True
    except:
        pass
    
    return jsonify(results)


# ==================== CHANNEL ANALYSIS ====================
@app.route('/api/analyze/channel', methods=['POST'])
def analyze_channel():
    data = request.json
    channel_name = data.get("channel_name", "")
    
    # Use channel analyzer
    from channel_analyzer import ChannelAnalyzer
    analyzer = ChannelAnalyzer()
    result = analyzer.analyze(channel_name)
    
    return jsonify(result)


# ==================== KEEP ALIVE (Render.com) ====================
@app.route('/api/keepalive', methods=['GET'])
def keepalive():
    """Prevent Render.com from sleeping"""
    return jsonify({"alive": True, "time": datetime.now().isoformat()})


# Keep-alive cron job (pings itself every 14 minutes)
def keep_alive_job():
    """Ping self to prevent Render free tier from sleeping"""
    import requests
    try:
        url = os.environ.get('RENDER_EXTERNAL_URL', 'http://localhost:5000')
        requests.get(f"{url}/api/keepalive", timeout=10)
    except:
        pass

scheduler.add_job(keep_alive_job, 'interval', minutes=14, id='keepalive')


# ==================== RUN ====================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)