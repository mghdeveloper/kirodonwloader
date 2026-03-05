import subprocess
import threading
import datetime
from flask import Flask, request, Response, jsonify

app = Flask(__name__)

LOG_FILE = "yt_dlp_errors.log"


# ==============================
# Logger
# ==============================
def log(message):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n[{datetime.datetime.utcnow()} UTC]\n")
        f.write(message)
        f.write("\n" + "=" * 80 + "\n")


# ==============================
# Home
# ==============================
@app.route("/")
def home():
    return jsonify({"status": "Advanced HLS Downloader Running"})


# ==============================
# Stream Endpoint
# ==============================
@app.route("/stream")
def stream():
    url = request.args.get("url")
    referer = request.args.get("referer")
    ua = request.args.get("ua")
    cookies = request.args.get("cookies")

    if not url:
        return jsonify({"error": "Missing url parameter"}), 400

    cmd = [
        "yt-dlp",
        url,
        "-o", "-",                        # output to stdout
        "--no-playlist",
        "--downloader", "ffmpeg",
        "--hls-use-mpegts",
        "--downloader-args", "ffmpeg_i:-allowed_extensions ALL",
        "--no-check-certificate",
        "--quiet"
    ]

    # Headers
    if referer:
        cmd += ["--add-header", f"Referer:{referer}"]

    if ua:
        cmd += ["--add-header", f"User-Agent:{ua}"]

    if cookies:
        cmd += ["--add-header", f"Cookie:{cookies}"]

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0
        )

        # Capture full stderr
        stderr_output = []

        def read_stderr():
            for line in process.stderr:
                decoded = line.decode("utf-8", errors="ignore")
                stderr_output.append(decoded)

        threading.Thread(target=read_stderr, daemon=True).start()

        def generate():
            try:
                while True:
                    chunk = process.stdout.read(1024 * 64)
                    if not chunk:
                        break
                    yield chunk
            except Exception as e:
                log("STREAM ERROR:\n" + str(e))
            finally:
                process.stdout.close()
                process.wait()

                # Log full command + stderr
                full_log = (
                    "COMMAND:\n" + " ".join(cmd) +
                    "\n\nSTDERR:\n" + "".join(stderr_output)
                )
                log(full_log)

        return Response(
            generate(),
            content_type="video/mp2t",
            headers={
                "Content-Disposition": "attachment; filename=video.ts",
                "Transfer-Encoding": "chunked"
            }
        )

    except Exception as e:
        log("PYTHON ERROR:\n" + str(e))
        return jsonify({
            "error": "Failed to start download",
            "details": str(e)
        }), 500


# ==============================
# Logs Viewer
# ==============================
@app.route("/logs")
def logs():
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            return Response(f.read(), mimetype="text/plain")
    except FileNotFoundError:
        return "No logs yet."


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
