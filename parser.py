import os
import asyncio
import random
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from supabase import create_client

# --- НАСТРОЙКИ SUPABASE ---
# Код сначала ищет ключи в секретах GitHub, если их нет — берет локальные для теста
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")

if not URL or not KEY:
    URL = "https://qenfvaqhbbqmorhvwmxg.supabase.co"
    KEY = "sb_secret_JCr9KEjlFpMBO3fymu5l-w_AHPa7qac"

supabase = create_client(URL, KEY)

async def scrape_details(context, url):
    """Заходит внутрь каждой машины и проверяет статус"""
    page = await context.new_page()
    try:
        # Увеличиваем таймаут для стабильности в облаке
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(random.uniform(2, 4))

        soup = BeautifulSoup(await page.content(), 'html.parser')
        
        # Пытаемся найти заголовок
        title_tag = soup.find(['h1', 'h4'])
        title = title_tag.get_text(strip=True).upper() if title_tag else "БЕЗ НАЗВАНИЯ"

        # ПРОВЕРКА НА ПРОДАНО
        if "[SOLDOUT]" in title or "SOLD" in title:
            print(f"⏩ ПРОПУСК: {title} (Продано)")
            return None

        # Собираем данные для базы
        description = soup.find('div', class_='entry-content')
        desc_text = description.get_text(strip=True)[:500] if description else ""
        
        imgs = [img['src'] for img in soup.find_all('img') if 'cdn' in img.get('src', '')]
        main_img = imgs[0] if imgs else ""

        car_data = {
            "external_id": url.split('/')[-1].split('?')[0],
            "brand_model": title,
            "description": desc_text,
            "image_url": main_img,
            "source_url": url
        }
        
        # Сохранение в Supabase
        try:
            supabase.table("cars").upsert(car_data).execute()
            print(f"✅ ДОБАВЛЕНО: {title}")
        except Exception as e:
            print(f"❌ Ошибка базы: {e}")

    except Exception as e:
        print(f"⚠️ Ошибка на странице {url}: {e}")
    finally:
        await page.close()

async def run_parser():
    async with async_playwright() as p:
        # ВАЖНО: headless=True для работы на сервере GitHub
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0...")
        page = await context.new_page()

        print("🚀 Запуск парсера...")
        await page.goto("https://rbautotrade.com/inventory/", wait_until="networkidle")

        # Собираем все ссылки на машины
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        links = [a['href'] for a in soup.select('a[href*="/inventory/"]')]
        unique_links = list(set(links))

        print(f"🔎 Найдено ссылок: {len(unique_links)}")

        for link in unique_links:
            await scrape_details(context, link)

        await browser.close()
        print("🎉 ВСЁ! Проверь базу данных.")

if __name__ == "__main__":
    asyncio.run(run_parser())