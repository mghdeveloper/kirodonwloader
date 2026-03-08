import os
import asyncio
import aiohttp
import subprocess
from urllib.parse import urljoin

MAX_CONCURRENT = 12


def normalize_url(url):
    return url.replace("\\/", "/").replace("\\", "").strip()


async def fetch_text(session, url):
    async with session.get(url) as r:
        if r.status != 200:
            raise Exception(f"M3U8 request failed {r.status}")
        return await r.text()


async def fetch_segment(session, url):

    try:
        async with session.get(url) as r:

            if r.status != 200:
                print("[SEGMENT ERROR]", url, r.status)
                return None

            return await r.read()

    except Exception as e:

        print("[SEGMENT FAILED]", url, e)
        return None


async def download_all(m3u8_url, output, tasks, task_id):

    m3u8_url = normalize_url(m3u8_url)

    timeout = aiohttp.ClientTimeout(total=120)

    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT, family=2)

    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:

        print("Fetching playlist:", m3u8_url)

        playlist = await fetch_text(session, m3u8_url)

        lines = playlist.splitlines()

        segments = []

        for line in lines:

            if line and not line.startswith("#"):

                seg = urljoin(m3u8_url, line)

                segments.append(seg)

        total = len(segments)

        print("Segments found:", total)

        ts_file = output.replace(".mp4", ".ts")

        with open(ts_file, "wb") as outfile:

            for i, seg in enumerate(segments):

                data = await fetch_segment(session, seg)

                if data:
                    outfile.write(data)

                progress = int((i + 1) / total * 100)

                tasks[task_id]["progress"] = progress

                print(f"Progress {i+1}/{total} ({progress}%)")

    print("Converting TS → MP4")

    subprocess.run([
        "ffmpeg",
        "-loglevel",
        "error",
        "-i",
        ts_file,
        "-c",
        "copy",
        output
    ])

    os.remove(ts_file)

    tasks[task_id]["status"] = "done"
    tasks[task_id]["progress"] = 100


def convert_m3u8(url, output, tasks, task_id):

    asyncio.run(download_all(url, output, tasks, task_id))
