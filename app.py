import os
import subprocess
import uuid
import requests
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


def extract_m3u8(url):
    if ".m3u8" in url:
        return url

    try:
        r = requests.get(url, timeout=10)
        if ".m3u8" in r.text:
            start = r.text.find("http", r.text.find(".m3u8") - 200)
            end = r.text.find(".m3u8") + 5
            return r.text[start:end]
    except Exception as e:
        return None

    return None


@app.route("/download")
def download():
    url = request.args.get("url")
    referer = request.args.get("referer")  # optional
    user_agent = request.args.get("ua")    # optional

    if not url:
        return jsonify({"error": "Missing url parameter"}), 400

    m3u8_url = extract_m3u8(url)
    if not m3u8_url:
        return jsonify({"error": "No m3u8 found"}), 400

    output_file = os.path.join(DOWNLOAD_FOLDER, f"{uuid.uuid4()}.mp4")

    headers = []
    if referer:
        headers.append(f"Referer: {referer}")
    if user_agent:
        headers.append(f"User-Agent: {user_agent}")

    header_string = "\\r\\n".join(headers) if headers else ""

    cmd = [
        "ffmpeg",
        "-headers", header_string,
        "-i", m3u8_url,
        "-map", "0",
        "-c", "copy",
        "-c:s", "mov_text",
        "-loglevel", "error",
        output_file
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode != 0:
            return jsonify({
                "error": "Download failed",
                "ffmpeg_stderr": result.stderr,
                "ffmpeg_stdout": result.stdout,
                "command": " ".join(cmd)
            }), 500

        return send_file(output_file, as_attachment=True)

    except Exception as e:
        return jsonify({
            "error": "Server exception",
            "details": str(e)
        }), 500


@app.route("/")
def home():
    return jsonify({"status": "M3U8 Downloader API running"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
