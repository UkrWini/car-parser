import os
import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from supabase import create_client

# Настройки подключения
URL = os.environ.get("SUPABASE_URL", "https://qenfvaqhbbqmorhvwmxg.supabase.co")
KEY = os.environ.get("SUPABASE_KEY", "sb_secret_JCr9KEjlFpMBO3fymu5l-w_AHPa7qac")
supabase = create_client(URL, KEY)

async def scrape_details(context, url):
    # Улучшенный фильтр мусорных страниц
    blacklist = ["search=", "how-to-buy", "hot-deals", "stand-by", "auction", "car-listings"]
    if any(x in url for x in blacklist): return 
    
    page = await context.new_page()
    try:
        # Увеличиваем время ожидания для подгрузки фото
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(4) # Даем JS подгрузить картинки
        
        soup = BeautifulSoup(await page.content(), 'html.parser')
        
        # Поиск заголовка
        title_tag = soup.select_one('h1.entry-title') or soup.find('h1')
        title = title_tag.get_text(strip=True).upper() if title_tag else "UNKNOWN CAR"

        if any(word in title for word in ["SOLD", "ПРОДАНО", "RESERVED"]): return

        # МОЩНЫЙ ПОИСК КАРТИНКИ (специально для rbautotrade.com)
        img_url = ""
        # Пробуем найти основное изображение поста или первое из галереи
        img_tag = (
            soup.select_one('img.wp-post-image') or 
            soup.select_one('.elementor-image img') or 
            soup.select_one('.slick-active img') or
            soup.find('img', src=lambda x: x and 'uploads' in x and 'logo' not in x.lower())
        )
        
        if img_tag:
            img_url = img_tag.get('src') or img_tag.get('data-src') or ""
        
        if img_url and img_url.startswith('/'):
            img_url = "https://rbautotrade.com" + img_url

        car_data = {
            "external_id": url.split('/')[-1].split('?')[0] or f"id_{hash(title)}",
            "brand_model": title,
            "description": "Premium vehicle from South Korea. Verified condition.",
            "image_url": img_url,
            "source_url": url
        }
        
        # Сохранение в базу
        supabase.table("cars").upsert(car_data).execute()
        print(f"✅ Готово: {title}")

    except Exception as e: 
        print(f"⚠️ Ошибка на {url}: {e}")
    finally: 
        await page.close()

async def run_parser():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Маскируемся под обычный браузер
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = await context.new_page()
        
        print("🔗 Загрузка инвентаря...")
        await page.goto("https://rbautotrade.com/inventory/", wait_until="networkidle")
        
        links = [a['href'] for a in (BeautifulSoup(await page.content(), 'html.parser')).select('a[href*="/inventory/"]')]
        unique_links = list(set(links))
        
        print(f"🔎 Найдено ссылок: {len(unique_links)}. Начинаем парсинг первых 15...")
        
        for link in unique_links[:15]:
            await scrape_details(context, link)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_parser())