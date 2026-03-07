import requests
import subprocess
import threading
import queue
from flask import Flask, request, Response, abort
from urllib.parse import urljoin

app = Flask(__name__)

THREADS = 4


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

    print("[INFO] Segments:", len(segments), flush=True)

    return segments


def download_worker(seg_queue, out_queue, headers):

    session = requests.Session()

    while True:

        item = seg_queue.get()

        if item is None:
            break

        index, url = item

        try:

            r = session.get(url, headers=headers, stream=True)

            data = b''.join(r.iter_content(8192))

            out_queue.put((index, data))

            print(f"[SEGMENT] OK {index}", flush=True)

        except Exception as e:

            print(f"[SEGMENT] FAIL {index} {e}", flush=True)

        seg_queue.task_done()


def stream_video(m3u8_url, referer, ua):

    headers = {
        "Referer": referer,
        "User-Agent": ua
    }

    segments = parse_m3u8(m3u8_url, headers)

    seg_queue = queue.Queue()
    out_queue = queue.Queue()

    for i, seg in enumerate(segments):
        seg_queue.put((i, seg))

    workers = []

    for _ in range(THREADS):

        t = threading.Thread(
            target=download_worker,
            args=(seg_queue, out_queue, headers),
            daemon=True
        )

        t.start()
        workers.append(t)

    cmd = [
        "ffmpeg",
        "-loglevel", "error",
        "-i", "pipe:0",

        "-c", "copy",
        "-bsf:a", "aac_adtstoasc",

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

    def feed():

        received = {}

        next_index = 0

        while next_index < len(segments):

            idx, data = out_queue.get()

            received[idx] = data

            while next_index in received:

                try:
                    process.stdin.write(received[next_index])
                except BrokenPipeError:
                    print("[ERROR] FFmpeg pipe closed", flush=True)
                    return

                del received[next_index]

                next_index += 1

        process.stdin.close()

    threading.Thread(target=feed, daemon=True).start()

    while True:

        chunk = process.stdout.read(65536)

        if not chunk:
            break

        yield chunk

    print("[INFO] Stream finished", flush=True)


@app.route("/")
def home():
    return "Kiro Downloader Ready"


@app.route("/download")
def download():

    url = request.args.get("url")
    referer = request.args.get("referer", "")
    ua = request.args.get("ua", "Mozilla/5.0")

    if not url:
        abort(400, "Missing url")

    print("[INFO] Download request:", url, flush=True)

    return Response(
        stream_video(url, referer, ua),
        headers={
            "Content-Type": "video/mp4",
            "Content-Disposition": "attachment; filename=video.mp4"
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
