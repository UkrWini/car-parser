import os
import asyncio
import random
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from supabase import create_client

# Данные Supabase
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")
if not URL or not KEY:
    URL = "https://qenfvaqhbbqmorhvwmxg.supabase.co"
    KEY = "sb_secret_JCr9KEjlFpMBO3fymu5l-w_AHPa7qac"
supabase = create_client(URL, KEY)

async def scrape_details(context, url):
    """Заходит внутрь каждой машины"""
    page = await context.new_page()
    try:
        # Увеличиваем таймаут, так как сайт может подтормаживать
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(2)
        
        soup = BeautifulSoup(await page.content(), 'html.parser')
        title = soup.find(['h1', 'h4']).get_text(strip=True).upper() if soup.find(['h1', 'h4']) else ""
        
        # ГЛАВНОЕ УСЛОВИЕ: Пропуск проданных
        if "SOLD" in title or "RESERVED" in title:
            print(f"   ⏩ ПРОПУСК: {title[:30]}... (Продано)")
            return

        # Если не продано - собираем данные
        imgs = [i['src'] for i in soup.find_all('img', src=True) if 'post' in i['src']]
        
        car_data = {
            "external_id": url.split('/')[-1].split('?')[0],
            "brand_model": title.title(),
            "image_url": imgs[0] if imgs else "",
            "source_site": "rbautotrade.com"
        }
        
        supabase.table("cars").upsert(car_data, on_conflict="external_id").execute()
        print(f"   ✅ ДОБАВЛЕНО: {title[:30]}")

    except Exception as e:
        print(f"   ❌ Ошибка в карточке: {url[-10:]}...")
    finally:
        await page.close()

async def run_parser():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True) # Видим процесс
        context = await browser.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
        page = await context.new_page()

        for cp in range(1, 11):
            url = f"https://rbautotrade.com/posts/car-listings?page={cp}"
            print(f"\n📂 СТРАНИЦА {cp} -------------------------")
            
            try:
                await page.goto(url, wait_until="load", timeout=60000)
                await asyncio.sleep(4)
                
                # Собираем ВСЕ ссылки, которые ведут на объявления
                hrefs = await page.eval_on_selector_all("a", "elements => elements.map(e => e.href)")
                
                # Фильтруем: только те, что содержат /car-listings/ и имеют ID в конце
                valid_urls = list(set([h for h in hrefs if "/posts/car-listings/" in h and any(char.isdigit() for char in h.split('/')[-1])]))
                
                print(f"📊 Найдено потенциальных машин: {len(valid_urls)}")

                # Идем по каждой ссылке
                for car_url in valid_urls:
                    if car_url.strip('/').endswith('car-listings'): continue
                    await scrape_details(context, car_url)
                    await asyncio.sleep(random.uniform(1, 2))

            except Exception as e:
                print(f"⚠️ Страница {cp} не загрузилась. Иду дальше.")

        await browser.close()
        print("\n🎉 ВСЁ! Проверь базу данных.")

if __name__ == "__main__":
    asyncio.run(run_parser())