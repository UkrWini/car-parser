import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from supabase import create_client

# ВСТАВЬ СВОИ ДАННЫЕ СЮДА НАПРЯМУЮ
URL = "https://qenfvaqhbbqmorhvwmxg.supabase.co"
# Используй Service Role Key (секретный) для парсера!
KEY = "sb_secret_JCr9KEjlFpMBO3fymu5l-w_AHPa7qac" 

supabase = create_client(URL, KEY)

async def scrape_details(context, url):
    blacklist = ["search=", "how-to-buy", "hot-deals", "stand-by", "auction"]
    if any(x in url for x in blacklist): return 
    
    page = await context.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(5) # Ждем загрузки картинок
        
        soup = BeautifulSoup(await page.content(), 'html.parser')
        title_tag = soup.select_one('h1.entry-title') or soup.find('h1')
        title = title_tag.get_text(strip=True).upper() if title_tag else "UNKNOWN CAR"

        if any(word in title for word in ["SOLD", "ПРОДАНО"]): return

        # Улучшенный поиск фото
        img_url = ""
        img_tag = (
            soup.select_one('img.wp-post-image') or 
            soup.select_one('.elementor-image img') or 
            soup.find('img', src=lambda x: x and 'uploads' in x and 'logo' not in x.lower())
        )
        if img_tag:
            img_url = img_tag.get('src') or img_tag.get('data-src') or ""
        
        if img_url and img_url.startswith('/'):
            img_url = "https://rbautotrade.com" + img_url

        car_data = {
            "external_id": url.split('/')[-2] if url.endswith('/') else url.split('/')[-1],
            "brand_model": title,
            "description": "Premium Korea Stock",
            "image_url": img_url,
            "source_url": url
        }
        
        supabase.table("cars").upsert(car_data).execute()
        print(f"✅ Записано: {title}")

    except Exception as e: print(f"⚠️ Ошибка: {e}")
    finally: await page.close()

async def run_parser():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0")
        page = await context.new_page()
        await page.goto("https://rbautotrade.com/inventory/", wait_until="networkidle")
        
        soup = BeautifulSoup(await page.content(), 'html.parser')
        links = [a['href'] for a in soup.select('a[href*="/inventory/"]')]
        
        for link in list(set(links))[:10]: # Для теста берем 10
            await scrape_details(context, link)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_parser())