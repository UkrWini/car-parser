import asyncio
import random
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from supabase import create_client

# Подключение к твоей базе
URL = "https://qenfvaqhbbqmorhvwmxg.supabase.co"
KEY = "sb_secret_JCr9KEjlFpMBO3fymu5l-w_AHPa7qac" 
supabase = create_client(URL, KEY)

async def scrape_car_details(context, url):
    page = await context.new_page()
    try:
        print(f"🕵️ Захожу в машину: {url}")
        # Загружаем страницу и ждем, пока она реально прогрузится
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(random.uniform(5, 8)) # Даем время скриптам сайта
        
        # Листаем вниз, чтобы сработали ленивые загрузки фото
        await page.mouse.wheel(0, 2000)
        await asyncio.sleep(2)

        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')

        # 1. Заголовок
        title = soup.find('h1').get_text(strip=True).upper() if soup.find('h1') else "KOREAN CAR"
        
        # 2. ВСЕ фотографии (для галереи)
        images = []
        for img in soup.find_all('img', src=True):
            src = img['src']
            if 'uploads' in src and 'logo' not in src.lower() and 'thumb' not in src.lower():
                images.append(src)
        
        unique_images = list(dict.fromkeys(images))
        main_image = unique_images[0] if unique_images else ""
        
        # 3. Видео (если есть)
        video_url = ""
        iframe = soup.find('iframe', src=True)
        if iframe and 'youtube' in iframe['src']:
            video_url = iframe['src']

        # 4. Полное описание лота
        desc_box = soup.select_one('.elementor-widget-theme-post-content') or soup.select_one('.entry-content')
        description = desc_box.get_text(separator='\n', strip=True) if desc_box else ""

        car_data = {
            "external_id": url.strip('/').split('/')[-1],
            "brand_model": title,
            "description": description[:2000],
            "image_url": main_image,
            "source_url": url
            # Если добавишь в базу колонку video_url, раскомментируй ниже:
            # "video_url": video_url 
        }

        supabase.table("cars").upsert(car_data).execute()
        print(f"✅ Полные данные сохранены: {title}")

    except Exception as e:
        print(f"⚠️ Ошибка в карточке {url}: {e}")
    finally:
        await page.close()

async def run_parser():
    async with async_playwright() as p:
        # Запуск "невидимого" браузера
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            device_scale_factor=1,
        )
        
        page = await context.new_page()
        print("🌐 Заходим на страницу инвентаря напрямую...")
        
        try:
            # Переходим сразу на список машин
            await page.goto("https://rbautotrade.com/inventory/", wait_until="networkidle", timeout=60000)
            await asyncio.sleep(5)
            
            # Собираем ссылки на все машины на странице
            links = await page.eval_on_selector_all(
                "a[href*='/inventory/']", 
                "elements => elements.map(e => e.href)"
            )
            
            # Оставляем только уникальные и длинные ссылки (карточки)
            unique_links = list(set([l for l in links if len(l) > 40]))
            print(f"🔎 Найдено машин в листинге: {len(unique_links)}")

            for link in unique_links[:12]: # Берем первые 12 для начала
                await scrape_car_details(context, link)
                await asyncio.sleep(random.uniform(3, 6)) # Пауза как у человека

        except Exception as e:
            print(f"❌ Ошибка на главной: {e}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_parser())