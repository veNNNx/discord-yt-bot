import asyncio
import json
from typing import NamedTuple

from attrs import define
from discord.ext.commands import Context


class Queue(NamedTuple):
    url: str
    title: str


@define
class YtPlaylistHandler:
    async def get_remaining_urls_from_playlist(
        self, url: str, queue_list: list[Queue], ctx: Context
    ) -> None:
        await self._get_urls(url=url, queue_list=queue_list, ctx=ctx)

    @staticmethod
    async def _get_urls(url: str, queue_list: list[Queue], ctx: Context) -> None:
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
                    await ctx.send(
                        f"**Playlist gathered**, current queue length: {len(queue_list)}"
                    )
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

    @staticmethod
    async def _fetch_title_from_url(url: str) -> str:
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

    @staticmethod
    async def _fetch_playlist_title_from_url(url: str) -> str:
        process = await asyncio.create_subprocess_exec(
            "yt-dlp",
            "--dump-single-json",
            "--flat-playlist",
            url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, _ = await process.communicate()
            info = json.loads(stdout.decode("utf-8"))
            return info.get("title", "Unknown playlist")
        except Exception:
            return "Unknown playlist"
