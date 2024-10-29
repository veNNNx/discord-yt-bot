import asyncio
from typing import List, NamedTuple

from attrs import define


class Queue(NamedTuple):
    url: str
    title: str


@define
class PlaylistHandler:
    async def get_remaining_urls_from_playlist(
        self, url: str, queue_list: List[Queue]
    ) -> None:
        process = await asyncio.create_subprocess_exec(
            "yt-dlp",
            url,
            "--skip-download",
            "--no-warning",
            "--print",
            "title",
            "--print",
            "webpage_url",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            while True:
                title_line = await process.stdout.readline()
                if not title_line:
                    break

                title = title_line.decode("utf-8").strip()
                url_line = await process.stdout.readline()
                url = url_line.decode("utf-8").strip()

                if url:
                    que = Queue(url=url, title=title)
                    queue_list.append(que)
                    print(f"Added to queue: {que}")

        except Exception as e:
            print(f"An error occurred while processing the playlist: {e}")

        await process.wait()
