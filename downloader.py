import os
import requests
import subprocess
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

MAX_THREADS = 32


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

    hostHeader = urlparse(url).netloc

    return {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Host": hostHeader,
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

    temp = f"tmp_{task_id}"
    os.makedirs(temp, exist_ok=True)

    r = requests.get(url, headers=defaultHeaders)
    playlist = r.text.splitlines()

    segments = []

    for line in playlist:
        if line and not line.startswith("#"):
            segments.append(urljoin(url, line))

    total = len(segments)

    def download(i, seg):

        path = f"{temp}/{i}.ts"

        res = requests.get(seg, headers=segment_headers(seg), stream=True)

        with open(path, "wb") as f:
            for chunk in res.iter_content(8192):
                if chunk:
                    f.write(chunk)

        return i

    done = 0

    with ThreadPoolExecutor(MAX_THREADS) as exe:

        futures = [exe.submit(download, i, s) for i, s in enumerate(segments)]

        for f in as_completed(futures):

            done += 1
            tasks[task_id]["progress"] = int((done / total) * 100)

    with open(f"{temp}/list.txt", "w") as f:
        for i in range(total):
            f.write(f"file '{temp}/{i}.ts'\n")

    subprocess.run([
        "ffmpeg",
        "-loglevel", "error",
        "-f", "concat",
        "-safe", "0",
        "-i", f"{temp}/list.txt",
        "-c", "copy",
        output
    ])

    tasks[task_id]["status"] = "done"
    tasks[task_id]["progress"] = 100
