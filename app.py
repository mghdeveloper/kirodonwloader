import os
import subprocess
import uuid
from flask import Flask, request, Response, jsonify, send_file

app = Flask(__name__)

TEMP_DIR = "/tmp/videos"
os.makedirs(TEMP_DIR, exist_ok=True)


def convert_to_mp4(m3u8, referer, ua):

    vid = str(uuid.uuid4())
    out = f"{TEMP_DIR}/{vid}.mp4"

    cmd = [
        "ffmpeg",
        "-loglevel", "error",
        "-headers", f"Referer: {referer}\r\nUser-Agent: {ua}\r\n",
        "-i", m3u8,
        "-c", "copy",
        "-bsf:a", "aac_adtstoasc",
        "-movflags", "faststart",
        out
    ]

    subprocess.run(cmd)

    return vid, out


@app.route("/start")
def start():

    url = request.args.get("url")
    referer = request.args.get("referer", "")
    ua = request.args.get("ua", "Mozilla/5.0")

    vid, path = convert_to_mp4(url, referer, ua)

    size = os.path.getsize(path)

    return jsonify({
        "id": vid,
        "size": size
    })


@app.route("/chunk")
def chunk():

    vid = request.args.get("id")
    start = int(request.args.get("start", 0))
    length = int(request.args.get("length", 1048576))

    path = f"{TEMP_DIR}/{vid}.mp4"

    if not os.path.exists(path):
        return "file not ready", 404

    with open(path, "rb") as f:

        f.seek(start)
        data = f.read(length)

    return Response(data, mimetype="application/octet-stream")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
