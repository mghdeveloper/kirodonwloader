import subprocess
import threading
import datetime
import os
from flask import Flask, request, Response, jsonify

app = Flask(__name__)

LOG_FILE = "yt_dlp_errors.log"


def log_error(message):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.datetime.utcnow()} UTC]\n")
            f.write(message)
            f.write("\n" + "="*80 + "\n")
    except:
        pass


@app.route("/")
def home():
    return jsonify({"status": "Kiro Downloader Python Server Running"})


@app.route("/stream")
def stream():

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
        "--hls-use-mpegts",
        "--concurrent-fragments", "5",
        "--no-playlist",
        "--no-check-certificate",
        "--quiet"
    ]

    if referer:
        cmd += ["--add-header", f"Referer:{referer}"]

    if ua:
        cmd += ["--add-header", f"User-Agent:{ua}"]

    try:

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0
        )

        def capture_stderr():
            err = process.stderr.read().decode("utf-8", errors="ignore")
            if err.strip():
                log_error("COMMAND:\n" + " ".join(cmd) + "\n\nSTDERR:\n" + err)

        threading.Thread(target=capture_stderr, daemon=True).start()

        def generate():

            try:
                while True:

                    chunk = process.stdout.read(1024 * 256)

                    if not chunk:
                        break

                    yield chunk

            finally:
                try:
                    process.kill()
                except:
                    pass

        return Response(
            generate(),
            content_type="video/mp4",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"
            }
        )

    except Exception as e:

        log_error(str(e))

        return jsonify({"error": "stream failed"}), 500


if __name__ == "__main__":

    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port,
        threaded=True
    )
