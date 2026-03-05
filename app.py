import subprocess
import threading
import datetime
from flask import Flask, request, Response, jsonify

app = Flask(__name__)

LOG_FILE = "download_errors.log"


def log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n[{datetime.datetime.utcnow()}]\n{msg}\n")


@app.route("/")
def home():
    return {"status": "HLS downloader running"}


@app.route("/download")
def download():
    url = request.args.get("url")
    referer = request.args.get("referer")
    ua = request.args.get("ua")

    if not url:
        return jsonify({"error": "Missing url"}), 400

    cmd = [
        "yt-dlp",
        url,
        "-o", "-",
        "-f", "best",
        "--no-playlist",
        "--downloader", "ffmpeg",
        "--hls-use-mpegts",
        "--downloader-args",
        "ffmpeg:-allowed_extensions ALL",
        "--downloader-args",
        "ffmpeg:-protocol_whitelist file,http,https,tcp,tls",
        "--no-check-certificate"
    ]

    if referer:
        cmd += ["--add-header", f"Referer:{referer}"]

    if ua:
        cmd += ["--add-header", f"User-Agent:{ua}"]

    log("COMMAND:\n" + " ".join(cmd))

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        def log_errors():
            err = process.stderr.read().decode("utf-8", errors="ignore")
            if err.strip():
                log("STDERR:\n" + err)

        threading.Thread(target=log_errors, daemon=True).start()

        def stream():
            while True:
                chunk = process.stdout.read(1024 * 64)
                if not chunk:
                    break
                yield chunk

        return Response(
            stream(),
            content_type="video/mp2t",
            headers={
                "Content-Disposition": "attachment; filename=video.ts"
            }
        )

    except Exception as e:
        log("PYTHON ERROR:\n" + str(e))
        return jsonify({"error": str(e)}), 500


@app.route("/logs")
def logs():
    try:
        with open(LOG_FILE, "r") as f:
            return Response(f.read(), mimetype="text/plain")
    except:
        return "No logs yet"
