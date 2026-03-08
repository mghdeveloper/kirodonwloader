import os
import asyncio
import aiohttp
import subprocess
from urllib.parse import urljoin

MAX_CONCURRENT = 20  # adjust based on server CPU/memory


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
                print("[SEGMENT ERROR]", url, r.status)
        except Exception as e:
            print("[SEGMENT FAILED]", url, e)
        await asyncio.sleep(1)
    return None


async def worker(queue, session, results):
    while True:
        item = await queue.get()
        if item is None:
            break
        index, url = item
        data = await fetch_segment(session, url)
        results[index] = data
        queue.task_done()


async def download_all(m3u8_url, output, tasks, task_id):
    m3u8_url = normalize_url(m3u8_url)

    timeout = aiohttp.ClientTimeout(total=180)
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT, family=2)

    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        print("Fetching playlist:", m3u8_url)
        playlist = await fetch_text(session, m3u8_url)
        lines = playlist.splitlines()
        segments = [urljoin(m3u8_url, l) for l in lines if l and not l.startswith("#")]

        total = len(segments)
        print("Segments found:", total)

        queue = asyncio.Queue()
        results = [None] * total
        for i, seg in enumerate(segments):
            await queue.put((i, seg))

        workers = [asyncio.create_task(worker(queue, session, results)) for _ in range(MAX_CONCURRENT)]
        await queue.join()
        for _ in workers:
            await queue.put(None)
        await asyncio.gather(*workers)

    ts_file = output.replace(".mp4", ".ts")
    print("Writing TS file")
    with open(ts_file, "wb") as f:
        for i, data in enumerate(results):
            if data:
                f.write(data)
            progress = int((i + 1) / total * 100)
            tasks[task_id]["progress"] = progress
            if i % 20 == 0:
                print(f"Progress {i}/{total} ({progress}%)")

    print("Converting TS → MP4")
    subprocess.run([
        "ffmpeg",
        "-loglevel",
        "error",
        "-i", ts_file,
        "-c", "copy",
        output
    ])

    os.remove(ts_file)
    tasks[task_id]["status"] = "done"
    tasks[task_id]["progress"] = 100


def convert_m3u8(url, output, tasks, task_id):
    asyncio.run(download_all(url, output, tasks, task_id))
