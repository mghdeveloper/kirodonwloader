import os
import subprocess
from flask import Flask, request, Response, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({"status": "Streaming M3U8 Downloader Running"})


@app.route("/stream")
def stream_download():
    url = request.args.get("url")
    referer = request.args.get("referer")
    ua = request.args.get("ua")

    if not url:
        return jsonify({"error": "Missing url parameter"}), 400

    # Build FFmpeg command
    cmd = [
        "ffmpeg",
        "-allowed_extensions", "ALL",
        "-protocol_whitelist", "file,http,https,tcp,tls",
    ]

    # Add headers if provided
    headers = []
    if referer:
        headers.append(f"Referer: {referer}")
    if ua:
        headers.append(f"User-Agent: {ua}")

    if headers:
        header_string = "\\r\\n".join(headers)
        cmd += ["-headers", header_string]

    cmd += [
        "-i", url,
        "-map", "0",
        "-c", "copy",             # Copy audio/video without re-encoding
        "-c:s", "mov_text",       # Convert subtitles if exist
        "-movflags", "frag_keyframe+empty_moov",  # Make MP4 streamable
        "-f", "mp4",
        "pipe:1"                  # Output to stdout for streaming
    ]

    try:
        # Launch FFmpeg process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Stream stdout to browser
        return Response(
            process.stdout,
            content_type="video/mp4",
            headers={"Content-Disposition": "attachment; filename=video.mp4"}
        )

    except Exception as e:
        return jsonify({
            "error": "Streaming failed",
            "details": str(e)
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
