import asyncio
import httpx
import os
import sys

# Add backend to path to import config
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.config import get_settings

async def test_newsapi():
    settings = get_settings()
    api_key = os.getenv('NEWS_API_KEY') or settings.news_api_key
    
    if not api_key:
        print("❌ NEWS_API_KEY not found in env or settings")
        return

    url = "https://newsapi.org/v2/top-headlines"
    params = {
        "q": "tech",
        "pageSize": 5,
        "apiKey": api_key,
        "language": "en"
    }
    
    print(f"📡 Testing NewsAPI.org...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            print("✅ Success!")
            print(f"📊 Total results: {data.get('totalResults')}")
            articles = data.get('articles', [])
            if articles:
                first = articles[0]
                print(f"📰 First result: {first.get('title')}")
                print(f"🏢 Source: {first.get('source', {}).get('name')}")
                print(f"🔗 URL: {first.get('url')}")
            else:
                print("⚠️ No news articles found.")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_newsapi())
