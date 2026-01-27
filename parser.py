import os
import asyncio
import random
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from supabase import create_client

# Настройки Supabase: берем из секретов GitHub
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")

# Если запускаешь локально на Mac, подставь свои строки здесь:
if not URL or not KEY:
    URL = "https://qenfvaqhbbqmorhvwmxg.supabase.co"
    KEY = "sb_secret_JCr9KEjlFpMBO3fymu5l-w_AHPa7qac"

supabase = create_client(URL, KEY)

async def scrape_details(context, url):
    page = await context.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(random.uniform(1, 3))
        soup = BeautifulSoup(await page.content(), 'html.parser')
        
        title_tag = soup.find(['h1', 'h4'])
        title = title_tag.get_text(strip=True).upper() if title_tag else "БЕЗ НАЗВАНИЯ"

        if "[SOLDOUT]" in title or "SOLD" in title:
            print(f"⏩ ПРОПУСК: {title}")
            return

        description = soup.find('div', class_='entry-content')
        desc_text = description.get_text(strip=True)[:500] if description else ""
        imgs = [img['src'] for img in soup.find_all('img') if 'cdn' in img.get('src', '')]
        
        car_data = {
            "external_id": url.split('/')[-1].strip('/'),
            "brand_model": title,
            "description": desc_text,
            "image_url": imgs[0] if imgs else "",
            "source_url": url
        }
        
        supabase.table("cars").upsert(car_data).execute()
        print(f"✅ ДОБАВЛЕНО: {title}")

    except Exception as e:
        print(f"⚠️ Ошибка на {url}: {e}")
    finally:
        await page.close()

async def run_parser():
    async with async_playwright() as p:
        # ГЛАВНОЕ ИСПРАВЛЕНИЕ: headless=True (обязательно для GitHub)
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        print("🚀 Запуск парсера в облаке...")
        await page.goto("https://rbautotrade.com/inventory/", wait_until="networkidle")

        links = [a['href'] for a in (BeautifulSoup(await page.content(), 'html.parser')).select('a[href*="/inventory/"]')]
        unique_links = list(set(links))
        print(f"🔎 Найдено авто: {len(unique_links)}")

        for link in unique_links:
            await scrape_details(context, link)

        await browser.close()
        print("🎉 Готово!")

if __name__ == "__main__":
    asyncio.run(run_parser())