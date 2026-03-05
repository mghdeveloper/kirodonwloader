import subprocess
import threading
import datetime
from flask import Flask, request, Response, jsonify

app = Flask(__name__)

LOG_FILE = "yt_dlp_errors.log"


def log_error(message):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.datetime.utcnow()} UTC]\n")
            f.write(message)
            f.write("\n" + "=" * 80 + "\n")
    except:
        pass


@app.route("/")
def home():
    return jsonify({"status": "YT-DLP Streaming Server Running"})


@app.route("/stream")
def stream_download():

    url = request.args.get("url")
    referer = request.args.get("referer")
    ua = request.args.get("ua")

    if not url:
        return jsonify({"error": "Missing url parameter"}), 400

    cmd = [
        "yt-dlp",
        url,
        "-o", "-",                    # stream to stdout
        "-f", "best",                 # avoid merge (prevents broken pipe)
        "--hls-use-mpegts",           # stable HLS streaming
        "--concurrent-fragments", "5",
        "--no-playlist",
        "--no-check-certificate",
        "--quiet"
    ]

    if referer:
        cmd += ["--add-header", f"Referer:{referer}"]

    if ua:
        cmd += ["--add-header", f"User-Agent:{ua}"]

    try:

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0
        )

        # Capture stderr in background
        def capture_errors():
            try:
                error_output = process.stderr.read().decode("utf-8", errors="ignore")
                if error_output.strip():
                    log_error(
                        "COMMAND:\n"
                        + " ".join(cmd)
                        + "\n\nSTDERR:\n"
                        + error_output
                    )
            except Exception as e:
                log_error("stderr capture failed: " + str(e))

        threading.Thread(target=capture_errors, daemon=True).start()

        def generate():

            try:
                while True:

                    chunk = process.stdout.read(1024 * 64)

                    if not chunk:
                        break

                    yield chunk

            except GeneratorExit:
                process.kill()

            except Exception as e:
                log_error("Streaming error: " + str(e))
                process.kill()

            finally:
                try:
                    process.stdout.close()
                    process.wait()
                except:
                    pass

        return Response(
            generate(),
            content_type="video/mp4",
            headers={
                "Content-Disposition": "attachment; filename=video.mp4",
                "Transfer-Encoding": "chunked",
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"
            }
        )

    except Exception as e:

        log_error("PYTHON ERROR:\n" + str(e))

        return jsonify({
            "error": "Streaming failed",
            "details": str(e)
        }), 500


@app.route("/logs")
def view_logs():

    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            return Response(f.read(), mimetype="text/plain")

    except FileNotFoundError:
        return "No logs yet."


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        threaded=True
    )
