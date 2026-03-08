import os
import uuid
import threading
import time
from flask import Flask, request, render_template, jsonify, Response
from downloader import convert_m3u8

app = Flask(__name__)

DOWNLOAD_DIR = "/tmp/downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

tasks = {}


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/convert", methods=["POST"])
def convert():
    data = request.get_json()
    m3u8_url = data.get("url")

    if not m3u8_url:
        return jsonify({"error": "missing url"}), 400

    task_id = str(uuid.uuid4())
    output_file = os.path.join(DOWNLOAD_DIR, f"{task_id}.mp4")

    tasks[task_id] = {
        "progress": 0,
        "status": "downloading",
        "file": output_file,
        "error": None
    }

    def run():
        try:
            convert_m3u8(m3u8_url, output_file, tasks, task_id)
        except Exception as e:
            tasks[task_id]["status"] = "error"
            tasks[task_id]["error"] = str(e)

    threading.Thread(target=run, daemon=True).start()

    return jsonify({"task_id": task_id})


@app.route("/progress/<task_id>")
def progress(task_id):
    if task_id not in tasks:
        return jsonify({"error": "task not found"}), 404
    return jsonify(tasks[task_id])


def stream_file(path):
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 512)
            if not chunk:
                break
            yield chunk


@app.route("/download/<task_id>")
def download(task_id):

    if task_id not in tasks:
        return {"error": "invalid task"}, 404

    path = tasks[task_id]["file"]

    if not os.path.exists(path):
        return {"error": "file not ready"}, 404

    return Response(
        stream_file(path),
        mimetype="video/mp4",
        headers={
            "Content-Disposition": f"attachment; filename={task_id}.mp4",
            "Cache-Control": "no-cache"
        }
    )


def cleanup_worker():
    while True:
        now = time.time()

        for tid in list(tasks.keys()):
            f = tasks[tid]["file"]

            if os.path.exists(f):
                if now - os.path.getmtime(f) > 3600:
                    os.remove(f)
                    tasks.pop(tid, None)

        time.sleep(120)


threading.Thread(target=cleanup_worker, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
