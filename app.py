import os
import uuid
from flask import Flask, request, render_template, jsonify, send_file
from downloader import convert_m3u8

app = Flask(__name__)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

tasks = {}

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/convert", methods=["POST"])
def convert():

    m3u8_url = request.json["url"]

    task_id = str(uuid.uuid4())
    output = f"{DOWNLOAD_DIR}/{task_id}.mp4"

    tasks[task_id] = {
        "progress": 0,
        "status": "downloading",
        "file": output
    }

    def run():
        convert_m3u8(m3u8_url, output, tasks, task_id)

    import threading
    threading.Thread(target=run).start()

    return jsonify({"task_id": task_id})


@app.route("/progress/<task_id>")
def progress(task_id):
    return jsonify(tasks.get(task_id, {}))


@app.route("/download/<task_id>")
def download(task_id):

    file = tasks[task_id]["file"]

    return send_file(file, as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
