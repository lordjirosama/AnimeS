import asyncio
import re
from datetime import datetime
from aiohttp import ClientSession

# Updated Query to accept 'type' (ANIME or MANGA)
ANIME_GRAPHQL_QUERY = """
query ($search: String, $type: MediaType) {
  Media (search: $search, type: $type) {
    id
    title { english romaji }
    type
    format
    status
    episodes
    chapters
    seasonYear
    genres
    description(asHtml: false)
  }
}
"""

class AniLister:
    def __init__(self, anime_name: str, year: int, media_type: str = "ANIME") -> None:
        self.__api = "https://graphql.anilist.co"
        self.__ani_name = anime_name
        self.__ani_year = year
        self.__vars = { "search": self.__ani_name, "type": media_type }  

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
                self.__ani_year -= 1
                self.__vars['seasonYear'] = self.__ani_year
                await asyncio.sleep(2)
                continue

            if res_code == 404:
                self.__vars = {'search': self.__ani_name, "type": self.__vars["type"]}
                await asyncio.sleep(2)
                continue

            if res_code == 429:
                retry_after = int(res_heads.get("Retry-After", 10))
                await asyncio.sleep(retry_after)
                continue

            if res_code in [500, 501, 502, 503]:
                await asyncio.sleep(5)
                continue

            await asyncio.sleep(3)
            
        return {}
