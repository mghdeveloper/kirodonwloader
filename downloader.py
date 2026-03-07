import os
import requests
import subprocess
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

MAX_THREADS = 16


defaultHeaders = {
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Connection": "keep-alive",
    "Origin": "https://megacloud.blog",
    "Referer": "https://megacloud.blog/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "cross-site",
    "sec-ch-ua": "\"Not:A-Brand\";v=\"99\", \"Google Chrome\";v=\"145\", \"Chromium\";v=\"145\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/145.0.0.0 Safari/537.36"
}


def segment_headers(url):

    host = urlparse(url).netloc

    return {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Host": host,
        "Origin": "https://megacloud.blog",
        "Referer": "https://megacloud.blog/",
        "sec-ch-ua": "\"Not:A-Brand\";v=\"99\", \"Google Chrome\";v=\"145\", \"Chromium\";v=\"145\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/145.0.0.0 Safari/537.36"
    }


def convert_m3u8(url, output, tasks, task_id):

    print("Fetching playlist:", url)

    temp_dir = os.path.abspath(f"tmp_{task_id}")
    os.makedirs(temp_dir, exist_ok=True)

    r = requests.get(url, headers=defaultHeaders)

    if r.status_code != 200:
        raise Exception(f"M3U8 request failed {r.status_code}")

    playlist = r.text.splitlines()

    segments = []

    for line in playlist:
        if line and not line.startswith("#"):
            segments.append(urljoin(url, line))

    total = len(segments)

    print("Total segments:", total)

    if total == 0:
        raise Exception("No segments found in playlist")

    def download_segment(i, seg_url):

        try:

            headers = segment_headers(seg_url)

            r = requests.get(seg_url, headers=headers, stream=True, timeout=20)

            if r.status_code != 200:
                print(f"[SEGMENT ERROR] {seg_url} -> {r.status_code}")
                return False

            path = os.path.join(temp_dir, f"{i}.ts")

            with open(path, "wb") as f:
                for chunk in r.iter_content(8192):
                    if chunk:
                        f.write(chunk)

            return True

        except Exception as e:

            print(f"[DOWNLOAD ERROR] {seg_url}")
            print(e)
            return False


    done = 0
    success = 0

    with ThreadPoolExecutor(MAX_THREADS) as exe:

        futures = {
            exe.submit(download_segment, i, seg): i
            for i, seg in enumerate(segments)
        }

        for future in as_completed(futures):

            done += 1

            if future.result():
                success += 1

            progress = int((done / total) * 100)

            tasks[task_id]["progress"] = progress

            print(f"Progress: {done}/{total} ({progress}%)")


    print("Segments downloaded:", success, "/", total)

    if success == 0:
        raise Exception("All segments failed")

    list_file = os.path.join(temp_dir, "list.txt")

    with open(list_file, "w") as f:
        for i in range(total):
            seg_path = os.path.abspath(os.path.join(temp_dir, f"{i}.ts"))
            if os.path.exists(seg_path):
                f.write(f"file '{seg_path}'\n")

    output = os.path.abspath(output)

    print("Merging with ffmpeg...")

    result = subprocess.run([
        "ffmpeg",
        "-loglevel",
        "error",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        list_file,
        "-c",
        "copy",
        output
    ], capture_output=True)

    if result.returncode != 0:

        print("FFMPEG ERROR:")
        print(result.stderr.decode())

        tasks[task_id]["status"] = "error"
        tasks[task_id]["error"] = result.stderr.decode()

        return

    print("MP4 created:", output)

    tasks[task_id]["status"] = "done"
    tasks[task_id]["progress"] = 100
