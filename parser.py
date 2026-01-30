import os
import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from supabase import create_client

URL = os.environ.get("SUPABASE_URL", "https://qenfvaqhbbqmorhvwmxg.supabase.co")
KEY = os.environ.get("SUPABASE_KEY", "sb_secret_JCr9KEjlFpMBO3fymu5l-w_AHPa7qac")
supabase = create_client(URL, KEY)

async def scrape_details(context, url):
    if "search=" in url or "how-to-buy" in url: return # Пропускаем мусорные ссылки
    
    page = await context.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(2)
        soup = BeautifulSoup(await page.content(), 'html.parser')
        
        # Улучшенный поиск заголовка для этого сайта
        title_tag = soup.select_one('h1.entry-title') or soup.find('h1') or soup.find('h4')
        title = title_tag.get_text(strip=True).upper() if title_tag else "БЕЗ НАЗВАНИЯ"

        if "SOLD" in title or "ПРОДАНО" in title: return

        # Ищем картинку
        img_tag = soup.select_one('.wp-post-image') or soup.find('img')
        img_url = img_tag.get('src') if img_tag else ""

        car_data = {
            "external_id": url.split('/')[-1].replace('?','_'),
            "brand_model": title,
            "description": "Premium car from Korea",
            "image_url": img_url,
            "source_url": url
        }
        
        supabase.table("cars").upsert(car_data).execute()
        print(f"✅ {title}")

    except Exception as e: print(f"⚠️ Ошибка: {e}")
    finally: await page.close()

async def run_parser():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto("https://rbautotrade.com/inventory/", wait_until="networkidle")
        
        links = [a['href'] for a in (BeautifulSoup(await page.content(), 'html.parser')).select('a[href*="/inventory/"]')]
        for link in list(set(links))[:15]: # Берем первые 15 для теста
            await scrape_details(context, link)
        await browser.close()

if __name__ == "__main__": asyncio.run(run_parser())