import subprocess
import threading
import datetime
from flask import Flask, request, Response, jsonify

app = Flask(__name__)

LOG_FILE = "yt_dlp_errors.log"

def log_error(message):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n[{datetime.datetime.utcnow()} UTC]\n")
        f.write(message)
        f.write("\n" + "="*80 + "\n")


@app.route("/")
def home():
    return jsonify({"status": "Stable HLS Streaming Downloader Running"})


@app.route("/stream")
def stream_download():
    url = request.args.get("url")
    referer = request.args.get("referer")
    ua = request.args.get("ua")

    if not url:
        return jsonify({"error": "Missing url parameter"}), 400

    cmd = [
        "yt-dlp",
        url,
        "-o", "-",  # output to stdout
        "-f", "best",
        "--no-playlist",
        "--downloader", "ffmpeg",
        "--hls-use-mpegts",
        "--no-check-certificate"
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
            bufsize=10**8
        )

        # Log stderr in background
        def capture_stderr():
            full_error = process.stderr.read().decode("utf-8", errors="ignore")
            if full_error.strip():
                log_error("COMMAND:\n" + " ".join(cmd) + "\n\nSTDERR:\n" + full_error)

        threading.Thread(target=capture_stderr, daemon=True).start()

        def generate():
            try:
                while True:
                    chunk = process.stdout.read(1024 * 64)
                    if not chunk:
                        break
                    yield chunk
            finally:
                process.stdout.close()
                process.wait()

        return Response(
            generate(),
            content_type="video/mp2t",  # MPEG-TS stream
            headers={
                "Content-Disposition": "attachment; filename=video.ts",
                "Transfer-Encoding": "chunked"
            }
        )

    except Exception as e:
        log_error("PYTHON ERROR:\n" + str(e))
        return jsonify({
            "error": "Streaming failed",
            "details": str(e)
        }), 500


@app.route("/logs")
def view_logs():
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            return Response(f.read(), mimetype="text/plain")
    except FileNotFoundError:
        return "No logs yet."


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
