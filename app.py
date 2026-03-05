import subprocess
import threading
import datetime
import os
import uuid
from flask import Flask, request, Response, jsonify, send_file

app = Flask(__name__)

LOG_FILE = "yt_dlp_errors.log"
DOWNLOAD_DIR = "downloads"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def log_error(message):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n[{datetime.datetime.utcnow()} UTC]\n")
        f.write(message)
        f.write("\n" + "=" * 80 + "\n")


@app.route("/")
def home():
    return jsonify({"status": "YT-DLP Download Server Running"})


@app.route("/download")
def download_video():

    url = request.args.get("url")
    referer = request.args.get("referer")
    ua = request.args.get("ua")

    if not url:
        return jsonify({"error": "Missing url parameter"}), 400

    file_id = str(uuid.uuid4())
    filepath = os.path.join(DOWNLOAD_DIR, f"{file_id}.mp4")

    cmd = [
        "yt-dlp",
        url,
        "-f", "best",
        "--hls-use-mpegts",
        "-o", filepath,
        "--no-playlist",
        "--no-check-certificate"
    ]

    if referer:
        cmd += ["--add-header", f"Referer:{referer}"]

    if ua:
        cmd += ["--add-header", f"User-Agent:{ua}"]

    try:

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        if result.returncode != 0:

            log_error(
                "COMMAND:\n"
                + " ".join(cmd)
                + "\n\nSTDERR:\n"
                + result.stderr.decode("utf-8", errors="ignore")
            )

            return jsonify({"error": "Download failed"}), 500

        return send_file(
            filepath,
            as_attachment=True,
            download_name="video.mp4",
            mimetype="video/mp4"
        )

    except Exception as e:

        log_error("PYTHON ERROR:\n" + str(e))

        return jsonify({
            "error": "Download failed",
            "details": str(e)
        }), 500


@app.route("/logs")
def logs():
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            return Response(f.read(), mimetype="text/plain")
    except:
        return "No logs yet"


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
