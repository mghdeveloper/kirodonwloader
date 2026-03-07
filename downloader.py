import os
import httpx
import subprocess
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

MAX_THREADS = 16

default_headers = {
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


def normalize_url(url):
    url = url.replace("\\/", "/")
    url = url.replace("\\", "")
    return url.strip()


def segment_headers(url):
    host = urlparse(url).netloc

    headers = default_headers.copy()
    headers["Host"] = host

    return headers


def convert_m3u8(url, output, tasks, task_id):

    url = normalize_url(url)

    print("Fetching playlist:", url)

    client = httpx.Client(http2=True, headers=default_headers, follow_redirects=True, timeout=60)

    r = client.get(url)

    if r.status_code != 200:
        raise Exception(f"M3U8 request failed {r.status_code}")

    playlist = r.text.splitlines()

    segments = []

    for line in playlist:
        if line and not line.startswith("#"):
            segments.append(urljoin(url, line))

    total = len(segments)

    print("Segments found:", total)

    temp_dir = os.path.abspath(f"tmp_{task_id}")
    os.makedirs(temp_dir, exist_ok=True)

    def download_segment(i, seg_url):

        try:

            headers = segment_headers(seg_url)

            r = client.get(seg_url, headers=headers)

            if r.status_code != 200:
                print(f"[SEGMENT ERROR] {seg_url} -> {r.status_code}")
                return False

            path = os.path.join(temp_dir, f"{i}.ts")

            with open(path, "wb") as f:
                f.write(r.content)

            return True

        except Exception as e:

            print(f"[DOWNLOAD ERROR] {seg_url}")
            print(e)

            return False


    done = 0
    success = 0

    with ThreadPoolExecutor(MAX_THREADS) as exe:

        futures = {
            exe.submit(download_segment, i, s): i
            for i, s in enumerate(segments)
        }

        for f in as_completed(futures):

            done += 1

            if f.result():
                success += 1

            progress = int((done / total) * 100)

            tasks[task_id]["progress"] = progress

            print(f"Progress: {done}/{total} ({progress}%)")


    print("Downloaded:", success, "/", total)

    if success == 0:
        raise Exception("No segments downloaded")

    list_file = os.path.join(temp_dir, "list.txt")

    with open(list_file, "w") as f:
        for i in range(total):

            seg = os.path.abspath(os.path.join(temp_dir, f"{i}.ts"))

            if os.path.exists(seg):
                f.write(f"file '{seg}'\n")

    output = os.path.abspath(output)

    print("Merging using ffmpeg")

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

        print("FFMPEG ERROR")
        print(result.stderr.decode())

        tasks[task_id]["status"] = "error"
        tasks[task_id]["error"] = result.stderr.decode()

        return

    print("MP4 created:", output)

    tasks[task_id]["status"] = "done"
    tasks[task_id]["progress"] = 100
