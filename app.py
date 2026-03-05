import os
import uuid
import subprocess
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


def run_command(cmd):
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    return result.returncode, result.stdout, result.stderr


@app.route("/")
def home():
    return jsonify({"status": "Advanced M3U8 Downloader Running"})


@app.route("/download")
def download():
    url = request.args.get("url")
    referer = request.args.get("referer")
    user_agent = request.args.get("ua")

    if not url:
        return jsonify({"error": "Missing url parameter"}), 400

    file_id = str(uuid.uuid4())
    output_path = os.path.join(DOWNLOAD_FOLDER, f"{file_id}.mp4")

    ############################################
    # 🔥 STEP 1: Try yt-dlp (Best Method)
    ############################################

    ytdlp_cmd = [
        "yt-dlp",
        url,
        "-o", output_path,
        "--merge-output-format", "mp4",
        "--embed-subs",
        "--write-subs",
        "--sub-lang", "all",
        "--no-playlist"
    ]

    if referer:
        ytdlp_cmd += ["--add-header", f"Referer:{referer}"]
    if user_agent:
        ytdlp_cmd += ["--add-header", f"User-Agent:{user_agent}"]

    code, out, err = run_command(ytdlp_cmd)

    if code == 0 and os.path.exists(output_path):
        return send_file(output_path, as_attachment=True)

    ############################################
    # 🔥 STEP 2: Fallback to Raw FFmpeg
    ############################################

    ffmpeg_cmd = [
        "ffmpeg",
        "-allowed_extensions", "ALL",
        "-protocol_whitelist", "file,http,https,tcp,tls",
        "-i", url,
        "-map", "0",
        "-c", "copy",
        "-c:s", "mov_text",
        output_path
    ]

    if referer or user_agent:
        headers = []
        if referer:
            headers.append(f"Referer: {referer}")
        if user_agent:
            headers.append(f"User-Agent: {user_agent}")
        header_string = "\\r\\n".join(headers)

        ffmpeg_cmd.insert(1, "-headers")
        ffmpeg_cmd.insert(2, header_string)

    code2, out2, err2 = run_command(ffmpeg_cmd)

    if code2 == 0 and os.path.exists(output_path):
        return send_file(output_path, as_attachment=True)

    ############################################
    # ❌ If Both Fail
    ############################################

    return jsonify({
        "error": "Download failed",
        "yt_dlp_error": err,
        "ffmpeg_error": err2,
        "yt_dlp_command": " ".join(ytdlp_cmd),
        "ffmpeg_command": " ".join(ffmpeg_cmd)
    }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
