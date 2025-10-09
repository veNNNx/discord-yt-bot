import json
from datetime import datetime
from pathlib import Path

from attrs import define
from discord.ext.commands import Context

from .yt_playlist_handler import YtPlaylistHandler

PLAYLIST_FILE = Path(__file__).resolve().parent.parent / "static" / "playlists.json"
PLAYLIST_LOG_FILE = (
    Path(__file__).resolve().parent.parent / "static" / "playlists_changes.jsonl"
)


@define
class MemoryPlaylistHandler:
    async def get_playlist_by_id(self, playlist_id: int) -> dict:
        playlist_id -= 1
        playlists = self._load_playlists()
        for p in playlists:
            if p["id"] == playlist_id:
                return p
        return {}

    def _load_playlists(self) -> list[dict]:
        if not PLAYLIST_FILE.exists():
            with open(PLAYLIST_FILE, "w", encoding="utf-8") as f:
                json.dump([], f, indent=4)
            return []
        with open(PLAYLIST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_playlists(self, playlists: list[dict]):
        with open(PLAYLIST_FILE, "w", encoding="utf-8") as f:
            json.dump(playlists, f, indent=4)

    async def create_playlist(self, ctx: Context, name: str):
        playlists = self._load_playlists()
        new_id = max((p["id"] for p in playlists), default=-1) + 1
        playlists.append({"id": new_id, "title": name, "data": []})
        self._save_playlists(playlists)

        await ctx.send(f"Playlist '{name}' created with ID {new_id + 1}!")

        self._log_change(
            user=str(ctx.author),
            action="CREATE_PLAYLIST",
            details={"playlist_id": new_id + 1, "title": name},
        )

    async def add_to_playlist(self, ctx: Context, playlist_id: int, url: str):
        playlists = self._load_playlists()
        json_playlist_id = playlist_id - 1
        if "list=" in url:
            title = await YtPlaylistHandler._fetch_playlist_title_from_url(url)
        else:
            title = await YtPlaylistHandler._fetch_title_from_url(url)

        for p in playlists:
            if p["id"] == json_playlist_id:
                new_item_id = max((item["id"] for item in p["data"]), default=-1) + 1
                new_item = {"id": new_item_id, "url": url, "title": title}

                p["data"].append(new_item)
                self._save_playlists(playlists)

                await ctx.send(f"Added '{title}' to playlist '{p['title']}'")
                self._log_change(
                    user=str(ctx.author),
                    action="ADD_TRACK",
                    details={"playlist_id": playlist_id, "title": title, "url": url},
                )
                return
        await ctx.send(f"Playlist with ID {playlist_id} not found.")

    async def remove_from_playlist(self, ctx: Context, playlist_id: int, track_id: int):
        playlists = self._load_playlists()
        json_playlist_id = playlist_id - 1
        json_track_id = track_id - 1
        for p in playlists:
            if p["id"] == json_playlist_id:
                for idx, item in enumerate(p["data"]):
                    if item["id"] == json_track_id:
                        removed = p["data"].pop(idx)
                        for new_idx, track in enumerate(p["data"]):
                            track["id"] = new_idx

                        self._save_playlists(playlists)

                        await ctx.send(
                            f"Removed '{removed['title']}' from playlist '{p['title']}'"
                        )

                        self._log_change(
                            user=str(ctx.author),
                            action="REMOVE_TRACK",
                            details={
                                "playlist_id": playlist_id,
                                "removed_title": removed["title"],
                            },
                        )
                        return
                await ctx.send(
                    f"Item with ID {track_id} not found in playlist '{p['title']}'"
                )
                return
        await ctx.send(f"Playlist with ID {playlist_id} not found.")

    async def show_playlists(self, ctx: Context):
        playlists = self._load_playlists()
        if not playlists:
            await ctx.send("No playlists found.")
            return

        display_lines = []

        for p in playlists:
            num_songs = len(p["data"])
            user_playlist_id = p["id"] + 1
            if num_songs > 15:
                display_lines.append(
                    f"{user_playlist_id}. {p['title']} (over 15 songs)"
                )
            else:
                display_lines.append(f"{user_playlist_id}. {p['title']}")
                for item in p["data"]:
                    display_lines.append(f"    {item['id'] + 1}. {item['title']}")

            display_lines.append("-" * 40)

        if display_lines and display_lines[-1] == "-" * 20:
            display_lines.pop()

        await ctx.send("Playlists:\n" + "\n".join(display_lines))

    async def show_playlist_content(self, ctx: Context, playlist_id: int):
        json_playlist_id = playlist_id - 1
        playlists = self._load_playlists()
        for p in playlists:
            if p["id"] == json_playlist_id:
                if not p["data"]:
                    await ctx.send(f"Playlist '{p['title']}' is empty.")
                    return

                display = "\n".join(
                    f"{item['id'] + 1}. {item['title']} ({item['url']})"
                    for item in p["data"]
                )
                await ctx.send(f"Playlist '{p['title']}':\n{display}")
                return
        await ctx.send(f"Playlist with ID {playlist_id} not found.")

    def _log_change(self, user: str, action: str, details: dict):
        log_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user": user,
            "action": action,
            "details": details,
        }

        PLAYLIST_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(PLAYLIST_LOG_FILE, "a", encoding="utf-8") as f:
            json.dump(log_entry, f, ensure_ascii=False)
            f.write("\n")
