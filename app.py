import subprocess
import threading
from flask import Flask, request, Response, abort

app = Flask(__name__)

FFMPEG = "ffmpeg"


def read_logs(pipe):
    """Print ffmpeg logs to console"""
    for line in iter(pipe.readline, b''):
        try:
            print("[FFMPEG]", line.decode("utf-8", errors="ignore").strip(), flush=True)
        except:
            pass


def stream_ffmpeg(url, referer, ua):

    headers = f"Referer: {referer}\r\nUser-Agent: {ua}\r\n"

    cmd = [
        FFMPEG,
        "-loglevel", "info",

        "-headers", headers,

        "-allowed_extensions", "ALL",
        "-protocol_whitelist", "file,http,https,tcp,tls",

        "-i", url,

        "-map", "0:v:0?",
        "-map", "0:a:0?",

        "-c", "copy",

        "-bsf:a", "aac_adtstoasc",

        "-movflags", "frag_keyframe+empty_moov+faststart",

        "-f", "mp4",
        "-"
    ]

    print("[INFO] Starting FFmpeg", flush=True)
    print("[INFO] URL:", url, flush=True)

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Thread لقراءة logs
    threading.Thread(target=read_logs, args=(process.stderr,), daemon=True).start()

    while True:
        chunk = process.stdout.read(65536)
        if not chunk:
            break
        yield chunk

    process.kill()
    print("[INFO] Stream finished", flush=True)


@app.route("/")
def home():
    return "Kiro Downloader Running"


@app.route("/download")
def download():

    url = request.args.get("url")
    referer = request.args.get("referer", "")
    ua = request.args.get("ua", "Mozilla/5.0")

    if not url:
        abort(400, "Missing url parameter")

    print("[INFO] Download request received", flush=True)
    print("[INFO] M3U8:", url, flush=True)

    return Response(
        stream_ffmpeg(url, referer, ua),
        headers={
            "Content-Type": "video/mp4",
            "Content-Disposition": "attachment; filename=video.mp4",
            "Cache-Control": "no-cache"
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
