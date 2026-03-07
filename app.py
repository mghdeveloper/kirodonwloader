import subprocess
import sys
from flask import Flask, request, Response, abort

app = Flask(__name__)

FFMPEG = "ffmpeg"


def ffmpeg_stream(url, referer, ua):

    headers = f"Referer: {referer}\r\nUser-Agent: {ua}\r\n"

    cmd = [
        FFMPEG,
        "-loglevel", "info",  # لعرض progress
        "-headers", headers,
        "-i", url,
        "-map", "0:v:0?",
        "-map", "0:a:0?",
        "-c", "copy",
        "-movflags", "frag_keyframe+empty_moov+faststart",
        "-f", "mp4",
        "-"
    ]

    print(f"[INFO] Starting download: {url}")
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=10**6
    )

    def stream():
        try:
            while True:
                chunk = process.stdout.read(65536)
                if not chunk:
                    break
                yield chunk

                # قراءة stderr لعرض progress
                err_line = process.stderr.readline()
                if err_line:
                    line = err_line.decode(errors="ignore").strip()
                    if "frame=" in line or "size=" in line:
                        print(f"[PROGRESS] {line}")
                    elif "404" in line or "failed" in line.lower():
                        print(f"[ERROR] {line}", file=sys.stderr)
        finally:
            process.kill()
            print("[INFO] Download finished / process killed")

    return stream()


@app.route("/")
def home():
    return "Kiro Streaming Downloader Ready"


@app.route("/download")
def download():
    url = request.args.get("url")
    referer = request.args.get("referer", "")
    ua = request.args.get("ua", "Mozilla/5.0")

    if not url:
        abort(400, "Missing url parameter")

    print(f"[INFO] Request received for URL: {url}")

    return Response(
        ffmpeg_stream(url, referer, ua),
        headers={
            "Content-Type": "video/mp4",
            "Content-Disposition": "attachment; filename=video.mp4",
            "Cache-Control": "no-cache"
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
