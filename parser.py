import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from supabase import create_client

# Данные подключения
URL = "https://qenfvaqhbbqmorhvwmxg.supabase.co"
KEY = "sb_secret_JCr9KEjlFpMBO3fymu5l-w_AHPa7qac" # Твой Secret Key

supabase = create_client(URL, KEY)

async def scrape_details(context, url):
    page = await context.new_page()
    try:
        # Заходим и просто ждём 5 секунд, не пытаясь искать селекторы сразу
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(5) 
        
        soup = BeautifulSoup(await page.content(), 'html.parser')
        
        # Заголовок
        title_tag = soup.select_one('h1.entry-title') or soup.find('h1')
        title = title_tag.get_text(strip=True).upper() if title_tag else "UNKNOWN CAR"

        # Картинка (ищем везде, где может быть)
        img_tag = soup.select_one('img.wp-post-image') or soup.select_one('.elementor-image img') or soup.find('img', src=lambda x: x and 'uploads' in x)
        img_url = img_tag.get('src') if img_tag else ""

        car_data = {
            "external_id": url.strip('/').split('/')[-1],
            "brand_model": title,
            "description": "Stock from Korea",
            "image_url": img_url,
            "source_url": url
        }
        
        supabase.table("cars").upsert(car_data).execute()
        print(f"✅ Готово: {title}")

    except Exception as e:
        print(f"⚠️ Ошибка на {url}: {e}")
    finally:
        await page.close()

async def run_parser():
    async with async_playwright() as p:
        # МАКСИМАЛЬНАЯ МАСКИРОВКА
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        print("🔗 Пробуем пробиться на сайт...")
        await page.goto("https://rbautotrade.com/inventory/", wait_until="domcontentloaded")
        await asyncio.sleep(7) # Даём сайту «прогрузиться»
        
        soup = BeautifulSoup(await page.content(), 'html.parser')
        
        # Собираем ссылки вручную, чтобы не зависеть от Playwright selectors
        links = []
        for a in soup.find_all('a', href=True):
            if '/inventory/' in a['href'] and a['href'] != "https://rbautotrade.com/inventory/":
                links.append(a['href'])
        
        unique_links = list(set(links))
        print(f"🔎 Найдено машин: {len(unique_links)}")
        
        for link in unique_links[:10]: # Берём 10 для теста
            await scrape_details(context, link)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_parser())