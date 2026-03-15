import os
import json
import uuid
import pickle
import threading
from datetime import datetime
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ============ SETUP ============
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)
for d in ["output/scripts", "output/audio", "output/videos",
          "output/temp", "credentials"]:
    os.makedirs(d, exist_ok=True)

# Setup YouTube credentials from ENV
yt_cred_json = os.environ.get("YOUTUBE_CLIENT_SECRET_JSON", "")
if yt_cred_json:
    try:
        cred_data = json.loads(yt_cred_json)
        cred_path = "credentials/youtube_client_secret.json"
        with open(cred_path, "w") as f:
            json.dump(cred_data, f, indent=2)
        print("YouTube credentials file created")
    except Exception as e:
        print(f"YouTube cred error: {e}")

bot_state = {
    "running": False,
    "auto_mode": False,
    "latest_log": "",
    "tasks": {}
}


def read_json(filename, default=None):
    path = os.path.join(DATA_DIR, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default if default is not None else {}


def write_json(filename, data):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


# ============ HOME ============
@app.route("/")
def home():
    return """
    <html>
    <head><title>Auto Video Bot</title></head>
    <body style="background:#0f172a;color:white;font-family:Arial;
                 display:flex;justify-content:center;align-items:center;
                 height:100vh;margin:0;">
        <div style="text-align:center;padding:40px;background:#1e293b;
                    border-radius:20px;">
            <h1>🤖 Auto Video Bot</h1>
            <p style="color:#22c55e;font-size:1.3em;">✅ Server Running!</p>
            <br>
            <a href="/api/ping" style="color:#818cf8;">Test API →</a>
        </div>
    </body>
    </html>
    """


# ============ API: PING ============
@app.route("/api/ping")
def ping():
    return jsonify({
        "status": "ok",
        "message": "Auto Video Bot is running!",
        "time": datetime.now().isoformat(),
        "bot_running": bot_state["running"],
        "auto_mode": bot_state["auto_mode"]
    })


# ============ API: SETTINGS ============
@app.route("/api/settings", methods=["GET"])
def get_settings():
    return jsonify(read_json("settings.json", {}))


@app.route("/api/settings", methods=["POST"])
def save_settings():
    data = request.json or {}
    existing = read_json("settings.json", {})
    existing.update(data)
    write_json("settings.json", existing)
    return jsonify({"success": True, "message": "Settings saved!"})


# ============ YOUTUBE AUTH ============
@app.route("/api/auth/youtube/url")
def youtube_auth_url():
    """Get YouTube OAuth URL - user clicks this to connect"""
    cred_path = "credentials/youtube_client_secret.json"

    if not os.path.exists(cred_path):
        return jsonify({
            "error": "YouTube credentials not configured",
            "help": "Add YOUTUBE_CLIENT_SECRET_JSON to Render environment variables"
        }), 400

    try:
        from google_auth_oauthlib.flow import Flow

        flow = Flow.from_client_secrets_file(
            cred_path,
            scopes=[
                "https://www.googleapis.com/auth/youtube.upload",
                "https://www.googleapis.com/auth/youtube"
            ],
            redirect_uri=request.host_url.rstrip("/") + "/api/auth/youtube/callback"
        )

        auth_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent"
        )

        # Save state
        write_json("youtube_auth_state.json", {"state": state})

        return jsonify({"auth_url": auth_url})

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/auth/youtube/callback")
def youtube_auth_callback():
    """YouTube OAuth callback - Google redirects here after user allows"""
    cred_path = "credentials/youtube_client_secret.json"

    try:
        from google_auth_oauthlib.flow import Flow

        flow = Flow.from_client_secrets_file(
            cred_path,
            scopes=[
                "https://www.googleapis.com/auth/youtube.upload",
                "https://www.googleapis.com/auth/youtube"
            ],
            redirect_uri=request.base_url
        )

        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials

        # Save token
        token_path = "credentials/yt_token.pickle"
        with open(token_path, "wb") as f:
            pickle.dump(credentials, f)

        print("YouTube token saved!")

        return """
        <html>
        <body style="background:#0f172a;color:white;font-family:Arial;
                     display:flex;justify-content:center;align-items:center;
                     height:100vh;margin:0;">
            <div style="text-align:center;padding:40px;background:#1e293b;
                        border-radius:20px;">
                <h1 style="color:#22c55e;">✅ YouTube Connected!</h1>
                <p>Your YouTube account is now connected.</p>
                <p>You can close this window.</p>
                <br>
                <p style="color:#94a3b8;">
                    Go back to your dashboard and refresh.
                </p>
            </div>
        </body>
        </html>
        """

    except Exception as e:
        return f"""
        <html>
        <body style="background:#0f172a;color:white;font-family:Arial;
                     display:flex;justify-content:center;align-items:center;
                     height:100vh;margin:0;">
            <div style="text-align:center;padding:40px;background:#1e293b;
                        border-radius:20px;">
                <h1 style="color:#ef4444;">❌ Error</h1>
                <p>{str(e)}</p>
                <br>
                <p style="color:#94a3b8;">Try again from dashboard.</p>
            </div>
        </body>
        </html>
        """, 400


# ============ TEST CONNECTIONS ============
@app.route("/api/test/connections")
def test_connections():
    yt_connected = False
    fb_connected = False

    # Check YouTube
    token_path = "credentials/yt_token.pickle"
    if os.path.exists(token_path):
        try:
            with open(token_path, "rb") as f:
                creds = pickle.load(f)
            if creds and (creds.valid or creds.refresh_token):
                yt_connected = True
        except:
            pass

    # Check Facebook
    fb_id = os.environ.get("FACEBOOK_PAGE_ID", "")
    fb_token = os.environ.get("FACEBOOK_ACCESS_TOKEN", "")
    settings = read_json("settings.json", {})
    fb_id = fb_id or settings.get("facebook_page_id", "")
    fb_token = fb_token or settings.get("facebook_token", "")
    fb_connected = bool(fb_id and fb_token)

    return jsonify({
        "youtube": yt_connected,
        "facebook": fb_connected
    })


# ============ VIDEO GENERATION ============
@app.route("/api/generate", methods=["POST"])
def generate_video():
    data = request.json or {}
    task_id = str(uuid.uuid4())[:8]

    bot_state["tasks"][task_id] = {
        "status": "started", "step": 1,
        "message": "Starting...",
        "created": datetime.now().isoformat()
    }

    thread = threading.Thread(
        target=run_pipeline,
        args=(task_id, data),
        daemon=True
    )
    thread.start()

    return jsonify({"task_id": task_id, "status": "started"})


@app.route("/api/generate/status/<task_id>")
def gen_status(task_id):
    return jsonify(bot_state["tasks"].get(task_id, {"status": "not_found"}))


def run_pipeline(task_id, options):
    import time as t

    try:
        settings = read_json("settings.json", {})
        config = {**settings, **options}
        topic = config.get("topic") or "सफलता के नियम"
        niche = config.get("channel_niche") or "motivation"

        # Step 1: Script
        bot_state["tasks"][task_id] = {
            "status": "processing", "step": 1,
            "message": "Generating AI script..."
        }
        script = generate_script(topic, niche)
        t.sleep(1)

        # Step 2: Voice
        bot_state["tasks"][task_id] = {
            "status": "processing", "step": 2,
            "message": "Creating voice over..."
        }

        audio_path = None
        srt_path = None
        try:
            import edge_tts
            import asyncio
            import re

            voice = config.get("voice", "hi-IN-SwaraNeural")
            text = script["script"].replace(" | ", "। ").replace("|", "। ")
            fname = re.sub(r'[^\w\s-]', '', topic)[:30]
            audio_path = f"output/audio/{fname}.mp3"
            srt_path = f"output/audio/{fname}.srt"

            async def make_audio():
                comm = edge_tts.Communicate(text=text, voice=voice)
                sub = edge_tts.SubMaker()
                with open(audio_path, "wb") as af:
                    async for chunk in comm.stream():
                        if chunk["type"] == "audio":
                            af.write(chunk["data"])
                        elif chunk["type"] == "WordBoundary":
                            sub.add(chunk["offset"], chunk["duration"], chunk["text"])
                with open(srt_path, "w", encoding="utf-8") as sf:
                    sf.write(sub.generate_srt())

            asyncio.run(make_audio())
        except Exception as e:
            print(f"Voice error: {e}")

        # Step 3: Video
        bot_state["tasks"][task_id] = {
            "status": "processing", "step": 3,
            "message": "Rendering video..."
        }

        video_path = None
        if audio_path and os.path.exists(audio_path):
            try:
                from moviepy.editor import AudioFileClip, ColorClip, CompositeVideoClip, TextClip
                import re as re2

                vtype = config.get("video_type", "short")
                w = 1080 if vtype == "short" else 1920
                h = 1920 if vtype == "short" else 1080

                audio_clip = AudioFileClip(audio_path)
                dur = audio_clip.duration
                bg = ColorClip(size=(w, h), color=(10, 10, 30), duration=dur)
                clips = [bg]

                try:
                    txt = TextClip(
                        script.get("hook", topic),
                        fontsize=40, color="white",
                        font="Arial-Bold", method="caption",
                        size=(w - 100, None), align="center",
                        stroke_color="black", stroke_width=2
                    )
                    txt = txt.set_position(("center", h - 400)).set_duration(dur)
                    clips.append(txt)
                except:
                    pass

                video = CompositeVideoClip(clips, size=(w, h))
                video = video.set_audio(audio_clip).set_duration(dur)

                fname2 = re2.sub(r'[^\w\s-]', '', topic)[:30]
                video_path = f"output/videos/{fname2}.mp4"

                video.write_videofile(
                    video_path, fps=24, codec="libx264",
                    audio_codec="aac", preset="ultrafast",
                    threads=2, logger=None
                )
                audio_clip.close()
                video.close()
            except Exception as e:
                print(f"Video error: {e}")

        # Step 4: Metadata
        bot_state["tasks"][task_id] = {
            "status": "processing", "step": 4,
            "message": "Generating metadata..."
        }
        t.sleep(1)

        # Step 5: Upload
        bot_state["tasks"][task_id] = {
            "status": "processing", "step": 5,
            "message": "Scheduling upload..."
        }

        upload_results = {}

        # YouTube Upload
        if config.get("upload_youtube") and video_path and os.path.exists(video_path):
            try:
                yt_result = upload_to_youtube(video_path, script, config)
                if yt_result:
                    upload_results["youtube"] = yt_result
            except Exception as e:
                upload_results["youtube_error"] = str(e)

        # Facebook Upload
        fb_id = config.get("facebook_page_id") or os.environ.get("FACEBOOK_PAGE_ID", "")
        fb_token = config.get("facebook_token") or os.environ.get("FACEBOOK_ACCESS_TOKEN", "")
        if config.get("upload_facebook") and fb_id and fb_token and video_path:
            try:
                import requests as req
                url = f"https://graph.facebook.com/v18.0/{fb_id}/videos"
                with open(video_path, "rb") as vf:
                    r = req.post(url, files={"source": vf},
                                data={"description": script.get("caption_facebook", ""),
                                      "access_token": fb_token}, timeout=300)
                fb_result = r.json()
                if "id" in fb_result:
                    upload_results["facebook"] = {"video_id": fb_result["id"]}
            except Exception as e:
                upload_results["facebook_error"] = str(e)

        t.sleep(1)

        # DONE
        bot_state["tasks"][task_id] = {
            "status": "completed", "step": 5,
            "message": "Video generated successfully!",
            "title": script.get("title_hindi", ""),
            "video_type": config.get("video_type", "short"),
            "tags": script.get("tags_english", [])[:10],
            "hashtags": script.get("hashtags", [])[:5],
            "youtube_url": (upload_results.get("youtube") or {}).get("url", ""),
            "upload_results": upload_results
        }

        videos = read_json("videos.json", [])
        videos.insert(0, {
            "id": task_id,
            "title": script.get("title_hindi", ""),
            "topic": topic,
            "duration": "60s",
            "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "status": "completed"
        })
        write_json("videos.json", videos)

        bot_state["latest_log"] = f"✅ {script.get('title_hindi', topic)}"

    except Exception as e:
        bot_state["tasks"][task_id] = {
            "status": "failed",
            "step": bot_state["tasks"].get(task_id, {}).get("step", 1),
            "message": str(e), "error": str(e)
        }
        bot_state["latest_log"] = f"❌ {e}"


def upload_to_youtube(video_path, script, config):
    """Upload video to YouTube"""
    token_path = "credentials/yt_token.pickle"
    if not os.path.exists(token_path):
        return None

    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    with open(token_path, "rb") as f:
        creds = pickle.load(f)

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(token_path, "wb") as f:
            pickle.dump(creds, f)

    youtube = build("youtube", "v3", credentials=creds)

    title = script.get("title_hindi", "Video")[:100]
    vtype = config.get("video_type", "short")
    if vtype == "short":
        title += " #shorts"

    body = {
        "snippet": {
            "title": title,
            "description": script.get("description", "")[:5000],
            "tags": script.get("tags_english", [])[:30],
            "categoryId": "22",
            "defaultLanguage": "hi"
        },
        "status": {"privacyStatus": "public"}
    }

    media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True)
    req = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        _, response = req.next_chunk()

    vid_id = response["id"]
    return {"video_id": vid_id, "url": f"https://youtube.com/watch?v={vid_id}"}


def generate_script(topic, niche="motivation"):
    try:
        import g4f
        import re
        prompt = (
            f'Create 60-second Hindi video script about: "{topic}". '
            f'Return ONLY valid JSON: '
            f'{{"topic":"{topic}","title_hindi":"title","title_english":"title",'
            f'"script":"line1। | line2। | line3।","hook":"hook",'
            f'"tags_english":["t1","t2","t3"],"tags_hindi":["ट1","ट2"],'
            f'"hashtags":["#t1","#t2","#t3","#t4","#t5"],'
            f'"description":"desc","caption_facebook":"caption"}}'
        )
        response = g4f.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        response = str(response).strip()
        if "```" in response:
            response = re.sub(r'```\w*\n?', '', response)
        s = response.find("{")
        e = response.rfind("}")
        if s != -1 and e != -1:
            data = json.loads(response[s:e + 1])
            if data.get("script"):
                return data
    except Exception as ex:
        print(f"AI error: {ex}")

    templates = {
        "motivation": {
            "script": "क्या आप सफल होना चाहते हैं? | तो ये वीडियो आपके लिए है। | सफलता का नियम है मेहनत। | कभी हार मत मानो। | सपनों को पूरा करो। | लाइक और सब्सक्राइब करें।",
            "hook": "क्या आप सफल होना चाहते हैं?"
        },
        "facts": {
            "script": "ये फैक्ट आपको चौंका देगा! | दुनिया में ऐसी बातें हैं जो हैरान करती हैं। | शहद कभी खराब नहीं होता। | इंसान का दिमाग दिन में साठ हज़ार बार सोचता है। | सब्सक्राइब करें।",
            "hook": "ये फैक्ट चौंका देगा!"
        },
        "tech": {
            "script": "ये hidden feature कम लोग जानते हैं! | सेटिंग्स में ये ऑन करो। | फोन फास्ट चलेगा। | सब्सक्राइब करें।",
            "hook": "ये trick जानते हो?"
        }
    }
    t = templates.get(niche, templates["motivation"])
    return {
        "topic": topic,
        "title_hindi": f"{topic} - जिंदगी बदल देगा",
        "title_english": f"{topic} - Must Watch",
        "script": t["script"], "hook": t["hook"],
        "tags_english": ["motivation", "hindi", "viral", "trending", "shorts"],
        "tags_hindi": ["मोटिवेशन", "प्रेरणा"],
        "hashtags": ["#motivation", "#hindi", "#viral", "#trending", "#shorts"],
        "description": f"{topic} | Hindi",
        "caption_facebook": f"🔥 {topic} #motivation #hindi"
    }


# ============ API: VIDEOS ============
@app.route("/api/videos")
def get_videos():
    return jsonify({"videos": read_json("videos.json", [])})

@app.route("/api/videos/<vid>", methods=["DELETE"])
def del_video(vid):
    vids = read_json("videos.json", [])
    vids = [v for v in vids if v.get("id") != vid]
    write_json("videos.json", vids)
    return jsonify({"success": True})


# ============ API: BOT ============
@app.route("/api/bot/status")
def bot_st():
    return jsonify(bot_state)

@app.route("/api/bot/start", methods=["POST"])
def bot_start():
    bot_state["running"] = True
    bot_state["latest_log"] = "🤖 Bot started!"
    return jsonify({"success": True})

@app.route("/api/bot/stop", methods=["POST"])
def bot_stop():
    bot_state["running"] = False
    bot_state["auto_mode"] = False
    return jsonify({"success": True})


# ============ API: AUTO ============
@app.route("/api/auto/start", methods=["POST"])
def auto_start():
    data = request.json or {}
    bot_state["auto_mode"] = True
    bot_state["running"] = True
    threading.Thread(
        target=run_pipeline,
        args=[f"auto_{uuid.uuid4().hex[:6]}", data],
        daemon=True
    ).start()
    return jsonify({"success": True})

@app.route("/api/auto/stop", methods=["POST"])
def auto_stop():
    bot_state["auto_mode"] = False
    return jsonify({"success": True})


# ============ API: ANALYTICS ============
@app.route("/api/analytics")
def analytics():
    v = read_json("videos.json", [])
    return jsonify({
        "total_videos": len(v),
        "youtube_uploads": 0,
        "facebook_uploads": 0,
        "uploaded": 0, "failed": 0, "scheduled": 0
    })

@app.route("/api/schedule")
def schedule():
    return jsonify({"jobs": []})

@app.route("/api/analyze/channel", methods=["POST"])
def analyze():
    return jsonify({
        "detected_niche": "motivation",
        "suggested_topics": ["सफलता", "मोटिवेशन", "Facts"],
        "hashtags": ["#hindi", "#viral"]
    })

@app.route("/api/keepalive")
def keepalive():
    return jsonify({"alive": True})


# ============ START ============
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
