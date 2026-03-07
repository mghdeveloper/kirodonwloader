import subprocess
import threading
import sys
from flask import Flask, request, Response, abort

app = Flask(__name__)

FFMPEG = "ffmpeg"


def log_reader(pipe):
    """Read ffmpeg logs continuously"""
    for line in iter(pipe.readline, b''):
        try:
            decoded = line.decode("utf-8", errors="ignore").strip()
            if decoded:
                print("[FFMPEG]", decoded, flush=True)
        except:
            pass


def ffmpeg_stream(url, referer, ua):

    headers = f"Referer: {referer}\r\nUser-Agent: {ua}\r\n"

    cmd = [
        FFMPEG,
        "-loglevel", "info",
        "-headers", headers,
        "-i", url,
        "-c", "copy",
        "-movflags", "frag_keyframe+empty_moov",
        "-f", "mp4",
        "-"
    ]

    print("[INFO] Running command:", " ".join(cmd), flush=True)

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # قراءة logs في thread منفصل
    threading.Thread(target=log_reader, args=(process.stderr,), daemon=True).start()

    while True:
        chunk = process.stdout.read(65536)
        if not chunk:
            break
        yield chunk

    print("[INFO] Stream finished", flush=True)


@app.route("/")
def home():
    return "Downloader ready"


@app.route("/download")
def download():

    url = request.args.get("url")
    referer = request.args.get("referer", "")
    ua = request.args.get("ua", "Mozilla/5.0")

    if not url:
        abort(400, "Missing url")

    print("[INFO] Download request:", url, flush=True)

    return Response(
        ffmpeg_stream(url, referer, ua),
        headers={
            "Content-Type": "video/mp4",
            "Content-Disposition": "attachment; filename=video.mp4"
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
