import asyncio
import random
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from supabase import create_client

# Подключение к Supabase
URL = "https://qenfvaqhbbqmorhvwmxg.supabase.co"
KEY = "sb_secret_JCr9KEjlFpMBO3fymu5l-w_AHPa7qac" 
supabase = create_client(URL, KEY)

async def human_delay():
    """Имитация человеческой паузы"""
    await asyncio.sleep(random.uniform(2, 5))

async def scrape_car_page(context, url):
    page = await context.new_page()
    try:
        # Эмуляция захода человека
        await page.goto(url, wait_until="networkidle", timeout=90000)
        await human_delay()
        
        # Прокрутка страницы вниз, чтобы подгрузились ленивые фото
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight/2)")
        await human_delay()

        soup = BeautifulSoup(await page.content(), 'html.parser')
        
        # 1. Заголовок
        title = soup.select_one('h1.entry-title').get_text(strip=True) if soup.select_one('h1.entry-title') else "Unknown Model"
        
        # 2. Все ссылки на фото (делаем массив для галереи)
        all_imgs = []
        for img in soup.find_all('img', src=True):
            src = img['src']
            if 'uploads' in src and 'logo' not in src.lower():
                all_imgs.append(src)
        
        # Основное фото — первое из списка
        main_image = all_imgs[0] if all_imgs else ""
        
        # 3. Описание (ищем текст лота)
        desc_box = soup.select_one('.elementor-text-editor') or soup.select_one('.entry-content')
        description = desc_box.get_text(separator=' ', strip=True)[:500] if desc_box else "Premium stock car."

        car_data = {
            "external_id": url.strip('/').split('/')[-1],
            "brand_model": title.upper(),
            "description": description,
            "image_url": main_image,
            "source_url": url,
            # Доп. поле, если ты добавил его в базу для галереи
            "gallery": all_imgs[:5] 
        }
        
        supabase.table("cars").upsert(car_data).execute()
        print(f"✅ Успешно обработан лот: {title}")

    except Exception as e:
        print(f"⚠️ Проблема с {url}: {e}")
    finally:
        await page.close()

async def run_parser():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True) # Ставим headless=True для GitHub
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        print("🌐 Заходим на главную...")
        await page.goto("https://rbautotrade.com/", wait_until="networkidle")
        await human_delay()
        
        # Ищем кнопку Car Listing и кликаем
        try:
            await page.click("text=CAR LISTING", timeout=10000)
            print("📂 Перешли в раздел Car Listing")
        except:
            await page.goto("https://rbautotrade.com/inventory/", wait_until="networkidle")
        
        await human_delay()
        
        # Собираем ссылки на карточки
        soup = BeautifulSoup(await page.content(), 'html.parser')
        links = []
        for a in soup.find_all('a', href=True):
            if '/inventory/' in a['href'] and a['href'] != "https://rbautotrade.com/inventory/":
                links.append(a['href'])
        
        unique_links = list(set(links))
        print(f"🔍 Найдено {len(unique_links)} автомобилей. Начинаем сбор данных...")
        
        for link in unique_links[:15]: # Берем первые 15 актуальных
            await scrape_car_page(context, link)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_parser())