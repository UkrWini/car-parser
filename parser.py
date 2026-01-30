import os
import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from supabase import create_client

# Данные подключения
URL = os.environ.get("SUPABASE_URL", "https://qenfvaqhbbqmorhvwmxg.supabase.co")
KEY = os.environ.get("SUPABASE_KEY", "sb_secret_JCr9KEjlFpMBO3fymu5l-w_AHPa7qac")
supabase = create_client(URL, KEY)

async def scrape_details(context, url):
    # Улучшенный фильтр мусорных страниц
    blacklist = ["search=", "how-to-buy", "hot-deals", "stand-by", "auction", "car-listings"]
    if any(x in url for x in blacklist): return 
    
    page = await context.new_page()
    try:
        # Ждем загрузки контента чуть дольше для картинок
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(3) 
        
        soup = BeautifulSoup(await page.content(), 'html.parser')
        
        # 1. Точный поиск заголовка
        title_tag = soup.select_one('h1.entry-title') or soup.find('h1')
        title = title_tag.get_text(strip=True).upper() if title_tag else "UNKNOWN CAR"

        # Пропускаем проданные авто
        if any(word in title for word in ["SOLD", "ПРОДАНО", "RESERVED"]): return

        # 2. Улучшенный поиск главного ФОТО
        # Ищем сначала по классу обложки, потом в слайдере, потом просто первую крупную картинку
        img_tag = (
            soup.select_one('img.wp-post-image') or 
            soup.select_one('.elementor-image img') or 
            soup.select_one('.attachment-full') or
            soup.find('img', src=lambda x: x and 'uploads' in x)
        )
        
        img_url = ""
        if img_tag:
            img_url = img_tag.get('src') or img_tag.get('data-src') or ""
        
        # Исправляем относительные ссылки
        if img_url and img_url.startswith('/'):
            img_url = "https://rbautotrade.com" + img_url

        car_data = {
            "external_id": url.split('/')[-1].split('?')[0] or "id_" + title[:10],
            "brand_model": title,
            "description": "Verified premium vehicle from South Korea",
            "image_url": img_url,
            "source_url": url
        }
        
        # Отправка в базу
        supabase.table("cars").upsert(car_data).execute()
        print(f"✅ Успешно: {title}")

    except Exception as e: 
        print(f"⚠️ Ошибка на {url}: {e}")
    finally: 
        await page.close()

async def run_parser():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0")
        page = await context.new_page()
        
        print("🔗 Заходим в инвентарь...")
        await page.goto("https://rbautotrade.com/inventory/", wait_until="networkidle")
        
        # Собираем все ссылки на карточки машин
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        links = [a['href'] for a in soup.select('a[href*="/inventory/"]')]
        unique_links = list(set(links))
        
        print(f"🔎 Найдено новых авто: {len(unique_links)}")
        
        # Парсим первые 20 машин
        for link in unique_links[:20]:
            await scrape_details(context, link)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_parser())