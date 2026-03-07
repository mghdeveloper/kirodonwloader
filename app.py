import subprocess
from flask import Flask, request, Response

app = Flask(__name__)

FFMPEG = "ffmpeg"


@app.route("/")
def home():
    return "Kiro Downloader Ready"


@app.route("/download")
def download():

    url = request.args.get("url")
    referer = request.args.get("referer", "")
    ua = request.args.get("ua", "Mozilla/5.0")

    if not url:
        return "Missing url", 400

    headers = f"Referer: {referer}\r\nUser-Agent: {ua}\r\n"

    cmd = [
        FFMPEG,
        "-loglevel", "error",
        "-headers", headers,
        "-i", url,

        # لا يعيد ترميز الفيديو (أسرع)
        "-c", "copy",

        # يجعل mp4 يبدأ البث فوراً
        "-movflags", "frag_keyframe+empty_moov",

        "-f", "mp4",
        "-"
    ]

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    def stream():
        while True:
            chunk = process.stdout.read(1024 * 64)
            if not chunk:
                break
            yield chunk

    return Response(
        stream(),
        headers={
            "Content-Type": "video/mp4",
            "Content-Disposition": "attachment; filename=video.mp4"
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
