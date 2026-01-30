import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from supabase import create_client

# Данные подключения (вшиты напрямую для надежности)
URL = "https://qenfvaqhbbqmorhvwmxg.supabase.co"
KEY = "sb_secret_JCr9KEjlFpMBO3fymu5l-w_AHPa7qac" 

supabase = create_client(URL, KEY)

async def scrape_details(context, url):
    page = await context.new_page()
    try:
        # Увеличиваем таймаут и ждем загрузки фото
        await page.goto(url, wait_until="networkidle", timeout=60000)
        await asyncio.sleep(5) 
        
        soup = BeautifulSoup(await page.content(), 'html.parser')
        
        # Поиск заголовка
        title_tag = soup.select_one('h1.entry-title') or soup.find('h1')
        title = title_tag.get_text(strip=True).upper() if title_tag else "UNKNOWN CAR"

        # Поиск фото (новый селектор для rbautotrade)
        img_tag = soup.select_one('img.wp-post-image') or soup.select_one('.elementor-image img')
        img_url = img_tag.get('src') if img_tag else ""
        
        if img_url and img_url.startswith('/'):
            img_url = "https://rbautotrade.com" + img_url

        car_data = {
            "external_id": url.split('/')[-2] if url.endswith('/') else url.split('/')[-1],
            "brand_model": title,
            "description": "Verified stock from Korea",
            "image_url": img_url,
            "source_url": url
        }
        
        # Отправка в базу
        supabase.table("cars").upsert(car_data).execute()
        print(f"✅ Записано: {title}")

    except Exception as e:
        print(f"⚠️ Ошибка на {url}: {e}")
    finally:
        await page.close()

async def run_parser():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0")
        page = await context.new_page()
        
        print("🔗 Открываем инвентарь...")
        await page.goto("https://rbautotrade.com/inventory/", wait_until="networkidle")
        
        # Ждем, пока загрузятся ссылки на машины
        await page.wait_for_selector('a[href*="/inventory/"]')
        
        soup = BeautifulSoup(await page.content(), 'html.parser')
        # Собираем ссылки, исключая саму страницу инвентаря
        all_links = [a['href'] for a in soup.select('a[href*="/inventory/"]')]
        links = list(set([l for l in all_links if l.strip('/') != "https://rbautotrade.com/inventory"]))
        
        print(f"🔎 Найдено машин: {len(links)}")
        
        for link in links[:12]: # Берем первые 12 для наполнения
            await scrape_details(context, link)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_parser())