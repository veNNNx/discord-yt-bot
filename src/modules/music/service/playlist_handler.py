import asyncio
from typing import NamedTuple

from attrs import define


class Queue(NamedTuple):
    url: str
    title: str


@define
class PlaylistHandler:
    async def get_remaining_urls_from_playlist(
        self,
        url: str,
        queue_list: list[Queue],
    ) -> None:
        await self._get_urls(url=url, queue_list=queue_list)

    async def _get_urls(
        self,
        url: str,
        queue_list: list[Queue],
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
                title_line = await process.stdout.readline()  # type: ignore[union-attr]
                if not title_line:
                    break
                title = title_line.decode("utf-8").strip()

                url_line = await process.stdout.readline()  # type: ignore[union-attr]
                url = url_line.decode("utf-8").strip()
                que = Queue(url=url, title=title)
                print(f"Add {que}")
                queue_list.append(que)

        except Exception as e:
            print(f"An error occurred: {e}")

        await process.wait()

    async def _fetch_title_from_url(self, url: str) -> str:
        process = await asyncio.create_subprocess_exec(
            "yt-dlp",
            "--get-title",
            url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, _ = await process.communicate()
            title = stdout.decode("utf-8").strip()
            return title
        except Exception:
            return "Unknwon"
