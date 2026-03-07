import requests
import subprocess
import threading
from flask import Flask, request, Response, abort
from urllib.parse import urljoin

app = Flask(__name__)

def read_logs(pipe):
    for line in iter(pipe.readline, b''):
        try:
            print("[FFMPEG]", line.decode(errors="ignore").strip(), flush=True)
        except:
            pass


def parse_m3u8(url, headers):

    print("[INFO] Fetching playlist", flush=True)

    r = requests.get(url, headers=headers)
    lines = r.text.splitlines()

    segments = []

    for line in lines:
        if line and not line.startswith("#"):
            segments.append(urljoin(url, line))

    print("[INFO] Segments found:", len(segments), flush=True)

    return segments


def stream_video(m3u8_url, referer, ua):

    headers = {
        "Referer": referer,
        "User-Agent": ua
    }

    segments = parse_m3u8(m3u8_url, headers)

    cmd = [
        "ffmpeg",
        "-loglevel", "info",
        "-i", "pipe:0",
        "-c", "copy",
        "-movflags", "frag_keyframe+empty_moov+faststart",
        "-f", "mp4",
        "pipe:1"
    ]

    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    threading.Thread(target=read_logs, args=(process.stderr,), daemon=True).start()

    def feed_segments():

        for i, seg in enumerate(segments):

            print(f"[SEGMENT] Downloading {i+1}/{len(segments)}", flush=True)

            r = requests.get(seg, headers=headers, stream=True)

            for chunk in r.iter_content(8192):
                process.stdin.write(chunk)

        process.stdin.close()

    threading.Thread(target=feed_segments, daemon=True).start()

    while True:
        chunk = process.stdout.read(65536)
        if not chunk:
            break
        yield chunk

    print("[INFO] Stream finished", flush=True)


@app.route("/")
def home():
    return "Kiro Proxy Downloader Ready"


@app.route("/download")
def download():

    url = request.args.get("url")
    referer = request.args.get("referer", "")
    ua = request.args.get("ua", "Mozilla/5.0")

    if not url:
        abort(400, "Missing url")

    print("[INFO] Download request received", flush=True)
    print("[INFO] M3U8:", url, flush=True)

    return Response(
        stream_video(url, referer, ua),
        headers={
            "Content-Type": "video/mp4",
            "Content-Disposition": "attachment; filename=video.mp4"
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
