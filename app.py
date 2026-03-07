import os
import uuid
import threading
from flask import Flask, request, render_template, jsonify, send_file

from downloader import convert_m3u8

app = Flask(__name__)

DOWNLOAD_DIR = os.path.abspath("downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

tasks = {}


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/convert", methods=["POST"])
def convert():

    data = request.get_json()

    m3u8_url = data["url"]

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
            print("FATAL ERROR:", e)
            tasks[task_id]["status"] = "error"
            tasks[task_id]["error"] = str(e)

    threading.Thread(target=run).start()

    return jsonify({"task_id": task_id})


@app.route("/progress/<task_id>")
def progress(task_id):

    if task_id not in tasks:
        return jsonify({"error": "task not found"}), 404

    return jsonify(tasks[task_id])


@app.route("/download/<task_id>")
def download(task_id):

    if task_id not in tasks:
        return {"error": "invalid task"}, 404

    file = tasks[task_id]["file"]

    if not os.path.exists(file):
        return {"error": "file not ready"}, 404

    return send_file(file, as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
