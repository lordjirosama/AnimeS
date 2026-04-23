import asyncio
from aiohttp import ClientSession

ANIME_GRAPHQL_QUERY = """
query ($search: String, $type: MediaType) {
  Page(page: 1, perPage: 1) {
    media(search: $search, type: $type, sort: POPULARITY_DESC) {
      id
      title { english romaji }
      type
      format
      status
      episodes
      chapters
      seasonYear
      season
      genres
      averageScore
      description(asHtml: false)
    }
  }
}
"""

class AniLister:
    def __init__(self, anime_name: str, year: int = None, media_type: str = "ANIME") -> None:
        self.__api = "https://graphql.anilist.co"
        self.__vars = {
            "search": anime_name,
            "type": media_type
        }

    async def post_data(self):
        async with ClientSession() as sess:
            async with sess.post(
                self.__api,
                json={"query": ANIME_GRAPHQL_QUERY, "variables": self.__vars}
            ) as resp:
                try:
                    data = await resp.json()
                except:
                    data = {}
                return resp.status, data

    async def get_anidata(self, retries: int = 3):
        for _ in range(retries):
            status, data = await self.post_data()

            if status == 200 and isinstance(data, dict):
                media_list = data.get("data", {}).get("Page", {}).get("media", [])

                if media_list:
                    return media_list[0]   # ✅ correct extraction

                return {}

            await asyncio.sleep(2)

        return {}
