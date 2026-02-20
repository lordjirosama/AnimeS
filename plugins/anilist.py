import asyncio
import re
from datetime import datetime
from aiohttp import ClientSession

ANIME_GRAPHQL_QUERY = """
query ($search: String) {
  Media (search: $search, type: ANIME) {
    id
    title { english romaji }
    format
    status
    episodes
    seasonYear
    genres
    description(asHtml: false)
  }
}
"""

class AniLister:
    def __init__(self, anime_name: str, year: int) -> None:
        self.__api = "https://graphql.anilist.co"
        self.__ani_name = anime_name
        self.__ani_year = year
        self.__vars = { "search": self.__ani_name }  

    # Yeh functions properly TextEditor se data lenge jab tu aage file rename me use karega
    def get_episode(self):
        return getattr(self, "pdata", {}).get("episode_number")

    def get_season(self):
        return getattr(self, "pdata", {}).get("anime_season")

    def get_audio(self):
        return getattr(self, "pdata", {}).get("audio")

    def __update_vars(self, year: bool = True) -> None:
        if year:
            self.__ani_year -= 1
            self.__vars['seasonYear'] = self.__ani_year
        else:
            self.__vars = {'search': self.__ani_name}

    async def post_data(self):
        async with ClientSession() as sess:
            async with sess.post(self.__api, json={'query': ANIME_GRAPHQL_QUERY, 'variables': self.__vars}) as resp:
                try:
                    json_data = await resp.json()
                except Exception:
                    text_data = await resp.text()
                    json_data = {"error_html": text_data[:200]}
                return resp.status, json_data, resp.headers

    async def get_anidata(self, retries: int = 5):
        for attempt in range(1, retries + 1):
            res_code, resp_json, res_heads = await self.post_data()

            if res_code == 200 and isinstance(resp_json, dict):
                return resp_json.get('data', {}).get('Media', {}) or {}

            if res_code == 404 and self.__ani_year > 2020:
                self.__update_vars()
                await asyncio.sleep(2)  # Fix: asleep changed to asyncio.sleep
                continue

            if res_code == 404:
                self.__update_vars(year=False)
                await asyncio.sleep(2)  # Fix: asleep changed to asyncio.sleep
                continue

            if res_code == 429:
                retry_after = int(res_heads.get("Retry-After", 10))
                await asyncio.sleep(retry_after)  # Fix: asleep changed to asyncio.sleep
                continue

            if res_code in [500, 501, 502, 503]:
                await asyncio.sleep(5)  # Fix: asleep changed to asyncio.sleep
                continue

            await asyncio.sleep(3)  # Fix: asleep changed to asyncio.sleep

        # Fix: Using print temporarily if rep.report is missing
        try:
            await rep.report(f"AniList data fetch failed for {self.__ani_name} after {retries} attempts.", "error", log=False)
        except NameError:
            print(f"AniList data fetch failed for {self.__ani_name}")
            
        return {}


# ⚠️ Note: TextEditor class tere baaki code (jaise file renamer) ke liye theek hai.
# Search (pm_search aur group_search) sirf AniLister class ka use karega.
class TextEditor:
    def __init__(self, name):
        self.__name = name
        self.adata = {}
        # Make sure 'parse' function is imported above
        try:
            self.pdata = parse(name) 
        except NameError:
            self.pdata = {}

    async def load_anilist(self):
        cache_names = []
        for option in [(False, False), (False, True), (True, False), (True, True)]:
            ani_name = await self.parse_name(*option)
            if ani_name in cache_names:
                continue
            cache_names.append(ani_name)
            self.adata = await AniLister(ani_name, datetime.now().year).get_anidata()
            if self.adata:
                break

    async def extract_metadata(self, filename: str):
        filename = filename.lower()

        ep_match = re.search(r'(?:ep?|episode)[\s._-]*?(\d{1,3})', filename)
        episode = ep_match.group(1) if ep_match else "01"

        quality_match = re.search(r'(360p|480p|720p|1080p|2160p)', filename)
        quality = quality_match.group(1) if quality_match else "720p"

        if re.search(r"\bdual[-_\s]?audio\b", filename):
            audio = "dual"
        elif re.search(r"\bmulti[-_\s]?audio\b", filename):
            audio = "multi"
        elif "dual" in filename:
            audio = "dual"
        elif "multi" in filename:
            audio = "multi"
        elif "jap" in filename and "eng" in filename:
            audio = "dual"
        elif "sub" in filename or "japanese" in filename:
            audio = "sub"
        else:
            audio = "sub"

        season_match = re.search(r'(?:s|season)[\s._-]*(\d{1,2})', filename)
        season = season_match.group(1).zfill(2) if season_match else "01"

        # Fix: Use update so previous data is not lost
        self.pdata.update({
            "episode": episode,
            "quality": quality,
            "audio": audio,
            "season": season
        })

    # @handle_logs - Uncomment this if you have the handle_logs decorator imported
    async def parse_name(self, no_s=False, no_y=False):
        anime_name = self.pdata.get("anime_title")
        anime_season = self.pdata.get("anime_season")
        anime_year = self.pdata.get("anime_year")
        if anime_name:
            pname = anime_name
            if not no_s and self.pdata.get("episode_number") and anime_season:
                pname += f" {anime_season}"
            if not no_y and anime_year:
                pname += f" {anime_year}"
            return pname
        return anime_name

    # @handle_logs
    async def get_id(self):
        if (ani_id := self.adata.get('id')) and str(ani_id).isdigit():
            return ani_id

    # @handle_logs
    async def get_poster(self):
        if anime_id := await self.get_id():
            return f"https://img.anili.st/media/{anime_id}"
        return "https://i.ibb.co/WvV8cmGc/photo-2025-05-06-02-54-16-7520721484596117512.jpg"
