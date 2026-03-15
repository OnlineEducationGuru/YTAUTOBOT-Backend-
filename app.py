import os
import json
import uuid
import threading
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ============ DATA STORAGE ============
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)
for d in ["output/scripts", "output/audio", "output/videos",
          "output/temp", "credentials"]:
    os.makedirs(d, exist_ok=True)

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


# ============ HOME PAGE ============
@app.route("/")
def home():
    return """
    <html>
    <head>
        <title>Auto Video Bot</title>
        <style>
            body {
                background: #0f172a;
                color: white;
                font-family: Arial, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }
            .container {
                text-align: center;
                padding: 40px;
                background: #1e293b;
                border-radius: 20px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            }
            h1 { font-size: 2.5em; margin-bottom: 10px; }
            .status {
                color: #22c55e;
                font-size: 1.3em;
                margin: 15px 0;
            }
            .dot {
                display: inline-block;
                width: 12px;
                height: 12px;
                background: #22c55e;
                border-radius: 50%;
                margin-right: 8px;
                animation: pulse 2s infinite;
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.4; }
            }
            a {
                color: #818cf8;
                text-decoration: none;
                font-size: 1.1em;
            }
            a:hover { text-decoration: underline; }
            .endpoints {
                margin-top: 20px;
                text-align: left;
                background: #0f172a;
                padding: 15px;
                border-radius: 10px;
                font-family: monospace;
                font-size: 0.9em;
            }
            .endpoints p {
                margin: 5px 0;
                color: #94a3b8;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 Auto Video Bot</h1>
            <div class="status">
                <span class="dot"></span>
                Server is Running!
            </div>
            <p style="color:#94a3b8;">
                YouTube & Facebook Auto Video Generator
            </p>
            <br>
            <a href="/api/ping">📡 Test API</a>
            <div class="endpoints">
                <p>✅ GET  /api/ping</p>
                <p>✅ POST /api/settings</p>
                <p>✅ POST /api/generate</p>
                <p>✅ GET  /api/videos</p>
                <p>✅ POST /api/bot/start</p>
                <p>✅ POST /api/auto/start</p>
                <p>✅ GET  /api/analytics</p>
            </div>
        </div>
    </body>
    </html>
    """


# ============ API: PING ============
@app.route("/api/ping")
def ping():
    return jsonify({
        "status": "ok",
        "message": "Auto Video Bot is running! 🤖",
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


# ============ API: GENERATE VIDEO ============
@app.route("/api/generate", methods=["POST"])
def generate_video():
    data = request.json or {}
    task_id = str(uuid.uuid4())[:8]

    bot_state["tasks"][task_id] = {
        "status": "started",
        "step": 1,
        "message": "Starting generation...",
        "created": datetime.now().isoformat()
    }

    thread = threading.Thread(
        target=run_pipeline,
        args=(task_id, data),
        daemon=True
    )
    thread.start()

    return jsonify({
        "task_id": task_id,
        "status": "started",
        "message": "Video generation started!"
    })


@app.route("/api/generate/status/<task_id>")
def gen_status(task_id):
    return jsonify(
        bot_state["tasks"].get(task_id, {"status": "not_found"})
    )


def run_pipeline(task_id, options):
    """Full video generation pipeline"""
    import time

    try:
        settings = read_json("settings.json", {})
        config = {**settings, **options}
        topic = config.get("topic") or "सफलता के नियम"
        niche = config.get("channel_niche") or "motivation"

        # ---- Step 1: Script ----
        bot_state["tasks"][task_id] = {
            "status": "processing", "step": 1,
            "message": "Generating AI script..."
        }

        script = generate_script(topic, niche)
        time.sleep(1)

        bot_state["tasks"][task_id] = {
            "status": "processing", "step": 2,
            "message": "Creating voice over..."
        }

        # ---- Step 2: Voice ----
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
                communicate = edge_tts.Communicate(text=text, voice=voice)
                submaker = edge_tts.SubMaker()
                with open(audio_path, "wb") as af:
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            af.write(chunk["data"])
                        elif chunk["type"] == "WordBoundary":
                            submaker.add(chunk["offset"],
                                        chunk["duration"],
                                        chunk["text"])
                with open(srt_path, "w", encoding="utf-8") as sf:
                    sf.write(submaker.generate_srt())

            asyncio.run(make_audio())
        except Exception as e:
            bot_state["tasks"][task_id]["message"] = f"Voice: {e}"
            audio_path = None

        # ---- Step 3: Video ----
        bot_state["tasks"][task_id] = {
            "status": "processing", "step": 3,
            "message": "Rendering video..."
        }

        video_path = None
        if audio_path and os.path.exists(audio_path):
            try:
                from moviepy.editor import (
                    AudioFileClip, ColorClip,
                    CompositeVideoClip, TextClip
                )
                import re as re2

                vtype = config.get("video_type", "short")
                w = 1080 if vtype == "short" else 1920
                h = 1920 if vtype == "short" else 1080

                audio_clip = AudioFileClip(audio_path)
                dur = audio_clip.duration

                bg = ColorClip(size=(w, h),
                              color=(10, 10, 30),
                              duration=dur)

                clips = [bg]

                # Add simple subtitle
                try:
                    hook = script.get("hook", topic)
                    txt = TextClip(
                        hook,
                        fontsize=40,
                        color="white",
                        font="Arial-Bold",
                        method="caption",
                        size=(w - 100, None),
                        align="center",
                        stroke_color="black",
                        stroke_width=2
                    )
                    txt = txt.set_position(("center", h - 400))
                    txt = txt.set_duration(dur)
                    clips.append(txt)
                except:
                    pass

                video = CompositeVideoClip(clips, size=(w, h))
                video = video.set_audio(audio_clip)
                video = video.set_duration(dur)

                fname2 = re2.sub(r'[^\w\s-]', '', topic)[:30]
                video_path = f"output/videos/{fname2}.mp4"

                video.write_videofile(
                    video_path,
                    fps=24,
                    codec="libx264",
                    audio_codec="aac",
                    preset="ultrafast",
                    threads=2,
                    logger=None
                )
                audio_clip.close()
                video.close()
            except Exception as e:
                bot_state["tasks"][task_id]["message"] = f"Video: {e}"
                video_path = None

        # ---- Step 4: Metadata ----
        bot_state["tasks"][task_id] = {
            "status": "processing", "step": 4,
            "message": "Generating metadata..."
        }
        time.sleep(1)

        # ---- Step 5: Schedule ----
        bot_state["tasks"][task_id] = {
            "status": "processing", "step": 5,
            "message": "Scheduling upload..."
        }

        upload_results = {}

        # YouTube upload
        if config.get("upload_youtube") and video_path:
            try:
                from youtube_uploader import YouTubeUploader
                yt = YouTubeUploader()
                if yt.youtube:
                    meta = {
                        "title": script.get("title_hindi", topic),
                        "description": script.get("description", ""),
                        "tags": script.get("tags_english", []),
                        "category_id": "22",
                        "privacy": "public"
                    }
                    result = yt.upload_video(video_path, meta)
                    upload_results["youtube"] = result
            except Exception as e:
                upload_results["youtube_error"] = str(e)

        # Facebook upload
        if (config.get("upload_facebook")
                and config.get("facebook_page_id")
                and video_path):
            try:
                from facebook_uploader import FacebookUploader
                fb = FacebookUploader()
                result = fb.upload_video(
                    video_path,
                    script.get("caption_facebook", ""),
                    " ".join(script.get("hashtags", []))
                )
                upload_results["facebook"] = result
            except Exception as e:
                upload_results["facebook_error"] = str(e)

        time.sleep(1)

        # ---- DONE ----
        bot_state["tasks"][task_id] = {
            "status": "completed",
            "step": 5,
            "message": "Video generated successfully!",
            "title": script.get("title_hindi", ""),
            "video_type": config.get("video_type", "short"),
            "tags": script.get("tags_english", [])[:10],
            "hashtags": script.get("hashtags", [])[:5],
            "youtube_url": (upload_results.get("youtube", {}) or {}).get("url", ""),
            "upload_results": upload_results
        }

        # Save record
        videos = read_json("videos.json", [])
        videos.insert(0, {
            "id": task_id,
            "title": script.get("title_hindi", ""),
            "topic": topic,
            "duration": "60s",
            "video_type": config.get("video_type", "short"),
            "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "status": "completed"
        })
        write_json("videos.json", videos)

        bot_state["latest_log"] = (
            f"✅ Video: {script.get('title_hindi', topic)}"
        )

    except Exception as e:
        bot_state["tasks"][task_id] = {
            "status": "failed",
            "step": bot_state["tasks"].get(
                task_id, {}
            ).get("step", 1),
            "message": str(e),
            "error": str(e)
        }
        bot_state["latest_log"] = f"❌ Failed: {e}"


def generate_script(topic, niche="motivation"):
    """Generate script - try AI first, fallback to templates"""

    # Try g4f
    try:
        import g4f
        prompt = (
            f'Create a 60-second Hindi video script about: "{topic}". '
            f'Return ONLY valid JSON: '
            f'{{"topic":"{topic}",'
            f'"title_hindi":"Hindi title",'
            f'"title_english":"English title",'
            f'"script":"sentence1। | sentence2। | sentence3।",'
            f'"hook":"hook line",'
            f'"tags_english":["tag1","tag2","tag3"],'
            f'"tags_hindi":["टैग1","टैग2"],'
            f'"hashtags":["#tag1","#tag2","#tag3","#tag4","#tag5"],'
            f'"description":"YouTube description",'
            f'"caption_facebook":"Facebook caption"}}'
        )

        response = g4f.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )

        import re
        response = str(response).strip()
        if "```" in response:
            response = re.sub(r'```\w*\n?', '', response)
        start = response.find("{")
        end = response.rfind("}")
        if start != -1 and end != -1:
            data = json.loads(response[start:end + 1])
            if data.get("script"):
                return data
    except Exception as e:
        print(f"AI script failed: {e}")

    # Fallback templates
    templates = {
        "motivation": {
            "script": (
                "क्या आप भी जिंदगी में सफल होना चाहते हैं? | "
                "तो ये वीडियो आपके लिए है। | "
                "सफलता का पहला नियम है कभी हार मत मानो। | "
                "हर सुबह एक नया मौका लेकर आती है। | "
                "अपने सपनों को कभी मत छोड़ो। | "
                "मेहनत कभी बेकार नहीं जाती। | "
                "जो आज मेहनत करते हैं कल दुनिया उनका नाम "
                "जानती है। | "
                "उठो जागो और तब तक मत रुको जब तक लक्ष्य "
                "पूरा न हो जाए। | "
                "लाइक और सब्सक्राइब जरूर करें।"
            ),
            "hook": "क्या आप सफल होना चाहते हैं?"
        },
        "facts": {
            "script": (
                "क्या आप जानते हैं ये हैरान कर देने वाला "
                "फैक्ट? | "
                "दुनिया में ऐसी बहुत सी बातें हैं जो आपको "
                "चौंका देंगी। | "
                "आज हम बताएंगे कुछ ऐसे ही रोचक तथ्य। | "
                "इंसान का दिमाग दिन में साठ हज़ार बार सोचता "
                "है। | "
                "शहद कभी खराब नहीं होता। | "
                "ऐसे और फैक्ट्स के लिए सब्सक्राइब करें।"
            ),
            "hook": "ये फैक्ट आपको चौंका देगा!"
        },
        "tech": {
            "script": (
                "आज मैं बताऊंगा एक ऐसी ट्रिक जो बहुत कम "
                "लोग जानते हैं। | "
                "ये hidden feature आपका फोन स्मार्ट बना "
                "देगी। | "
                "सेटिंग्स में जाइए और ये ऑप्शन ऑन कीजिए। | "
                "आपका फोन दोगुना फास्ट चलेगा। | "
                "ऐसी और टिप्स के लिए सब्सक्राइब करें।"
            ),
            "hook": "ये trick बहुत कम लोग जानते हैं!"
        },
        "health": {
            "script": (
                "सुबह उठकर ये एक काम करो सेहत बदल "
                "जाएगी। | "
                "खाली पेट गर्म पानी पीना चाहिए। | "
                "रोज़ तीस मिनट exercise करो। | "
                "ये छोटी आदतें जिंदगी बदल देंगी। | "
                "सब्सक्राइब करें।"
            ),
            "hook": "सुबह ये करो सेहत बदल जाएगी!"
        },
        "finance": {
            "script": (
                "अमीर बनना है तो ये बातें याद रखो। | "
                "पहला नियम बचत करो। | "
                "दूसरा नियम निवेश करो। | "
                "तीसरा नियम कर्ज मत लो। | "
                "चौथा नियम पैसे से पैसा कमाओ। | "
                "सब्सक्राइब करें।"
            ),
            "hook": "अमीर बनना है तो सुनो!"
        }
    }

    t = templates.get(niche, templates["motivation"])

    return {
        "topic": topic,
        "title_hindi": f"{topic} - जिंदगी बदल देगा",
        "title_english": f"{topic} - Must Watch",
        "script": t["script"],
        "hook": t["hook"],
        "tags_english": [
            "motivation", "hindi", "success",
            "viral", "trending", "shorts",
            "inspirational", "india"
        ],
        "tags_hindi": ["मोटिवेशन", "प्रेरणा", "सफलता"],
        "hashtags": [
            "#motivation", "#hindi", "#viral",
            "#trending", "#shorts"
        ],
        "description": f"{topic} | Hindi Video",
        "caption_facebook": f"🔥 {topic}\n#motivation #hindi #viral"
    }


# ============ API: VIDEOS ============
@app.route("/api/videos")
def get_videos():
    return jsonify({"videos": read_json("videos.json", [])})


@app.route("/api/videos/<video_id>", methods=["DELETE"])
def delete_video(video_id):
    videos = read_json("videos.json", [])
    videos = [v for v in videos if v.get("id") != video_id]
    write_json("videos.json", videos)
    return jsonify({"success": True})


# ============ API: BOT CONTROL ============
@app.route("/api/bot/status")
def bot_status():
    return jsonify({
        "running": bot_state["running"],
        "auto_mode": bot_state["auto_mode"],
        "latest_log": bot_state["latest_log"]
    })


@app.route("/api/bot/start", methods=["POST"])
def start_bot():
    bot_state["running"] = True
    bot_state["latest_log"] = "🤖 Bot started!"
    return jsonify({"success": True, "message": "Bot started!"})


@app.route("/api/bot/stop", methods=["POST"])
def stop_bot():
    bot_state["running"] = False
    bot_state["auto_mode"] = False
    bot_state["latest_log"] = "⏹ Bot stopped"
    return jsonify({"success": True, "message": "Bot stopped!"})


# ============ API: AUTO MODE ============
@app.route("/api/auto/start", methods=["POST"])
def auto_start():
    data = request.json or {}
    bot_state["auto_mode"] = True
    bot_state["running"] = True

    vpd = data.get("videos_per_day", 1)
    bot_state["latest_log"] = f"🤖 Auto: {vpd} videos/day"

    threading.Thread(
        target=run_pipeline,
        args=[f"auto_{uuid.uuid4().hex[:6]}", data],
        daemon=True
    ).start()

    return jsonify({
        "success": True,
        "message": f"Auto mode: {vpd} videos/day"
    })


@app.route("/api/auto/stop", methods=["POST"])
def auto_stop():
    bot_state["auto_mode"] = False
    bot_state["latest_log"] = "⏹ Auto mode stopped"
    return jsonify({"success": True})


# ============ API: ANALYTICS ============
@app.route("/api/analytics")
def analytics():
    videos = read_json("videos.json", [])
    return jsonify({
        "total_videos": len(videos),
        "youtube_uploads": 0,
        "facebook_uploads": 0,
        "uploaded": 0,
        "failed": 0,
        "scheduled": 0
    })


# ============ API: SCHEDULE ============
@app.route("/api/schedule")
def schedule():
    return jsonify({"jobs": []})


# ============ API: CONNECTIONS ============
@app.route("/api/test/connections")
def test_conn():
    yt = False
    fb = bool(os.environ.get("FACEBOOK_PAGE_ID"))

    try:
        cred_path = "credentials/youtube_client_secret.json"
        token_path = "credentials/yt_token.pickle"
        yt = os.path.exists(token_path)
    except:
        pass

    return jsonify({"youtube": yt, "facebook": fb})


@app.route("/api/auth/youtube/url")
def yt_auth():
    return jsonify({
        "message": "Setup YouTube OAuth in Google Cloud Console",
        "error": "Not configured yet"
    })


@app.route("/api/analyze/channel", methods=["POST"])
def analyze():
    data = request.json or {}
    name = data.get("channel_name", "")
    return jsonify({
        "channel_name": name,
        "detected_niche": "motivation",
        "suggested_topics": [
            "सफलता के नियम",
            "मोटिवेशनल कहानी",
            "Amazing Facts हिंदी में",
            "पैसे कैसे कमाएं"
        ],
        "hashtags": ["#hindi", "#viral", "#trending"]
    })


@app.route("/api/keepalive")
def keepalive():
    return jsonify({"alive": True, "time": datetime.now().isoformat()})


# ============ START SERVER ============
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"Starting on port {port}")
    app.run(host="0.0.0.0", port=port)
