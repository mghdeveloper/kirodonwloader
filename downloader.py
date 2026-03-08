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


async def fetch_segment(session, url, retries=3):
    for attempt in range(retries):
        try:
            async with session.get(url) as r:
                if r.status == 200:
                    return await r.read()
        except:
            pass
        await asyncio.sleep(1)
    return None


async def download_all(m3u8_url, output, tasks, task_id):

    m3u8_url = normalize_url(m3u8_url)

    timeout = aiohttp.ClientTimeout(total=300)

    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT)

    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:

        playlist = await fetch_text(session, m3u8_url)

        segments = [
            urljoin(m3u8_url, l)
            for l in playlist.splitlines()
            if l and not l.startswith("#")
        ]

        total = len(segments)

        ts_file = output.replace(".mp4", ".ts")

        with open(ts_file, "wb") as f:

            sem = asyncio.Semaphore(MAX_CONCURRENT)

            async def download_one(i, seg):

                async with sem:
                    data = await fetch_segment(session, seg)

                    if data:
                        f.write(data)

                    tasks[task_id]["progress"] = int((i + 1) / total * 100)

            await asyncio.gather(
                *[download_one(i, s) for i, s in enumerate(segments)]
            )

    subprocess.run([
        "ffmpeg",
        "-loglevel", "error",
        "-y",
        "-i", ts_file,
        "-c", "copy",
        output
    ])

    os.remove(ts_file)

    tasks[task_id]["status"] = "done"
    tasks[task_id]["progress"] = 100


def convert_m3u8(url, output, tasks, task_id):
    asyncio.run(download_all(url, output, tasks, task_id))
