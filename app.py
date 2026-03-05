import os
import subprocess
import uuid
import requests
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


def extract_m3u8(url):
    """
    If URL already contains .m3u8 return it,
    otherwise try to extract from page source.
    """
    if ".m3u8" in url:
        return url

    try:
        r = requests.get(url, timeout=10)
        if ".m3u8" in r.text:
            start = r.text.find("http", r.text.find(".m3u8") - 200)
            end = r.text.find(".m3u8") + 5
            return r.text[start:end]
    except:
        pass

    return None


@app.route("/download")
def download():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "Missing url parameter"}), 400

    m3u8_url = extract_m3u8(url)
    if not m3u8_url:
        return jsonify({"error": "No m3u8 found"}), 400

    output_file = os.path.join(DOWNLOAD_FOLDER, f"{uuid.uuid4()}.mp4")

    cmd = [
        "ffmpeg",
        "-i", m3u8_url,
        "-c", "copy",
        "-c:s", "mov_text",  # integrate subtitles if exist
        output_file
    ]

    try:
        subprocess.run(cmd, check=True)
        return send_file(output_file, as_attachment=True)
    except subprocess.CalledProcessError:
        return jsonify({"error": "Download failed"}), 500


@app.route("/")
def home():
    return jsonify({"status": "M3U8 Downloader API running"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
