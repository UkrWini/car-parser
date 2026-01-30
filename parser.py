import asyncio
import random
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from supabase import create_client

# Твои данные подключения
URL = "https://qenfvaqhbbqmorhvwmxg.supabase.co"
KEY = "sb_secret_JCr9KEjlFpMBO3fymu5l-w_AHPa7qac" 
supabase = create_client(URL, KEY)

async def human_behavior(page):
    """Имитация хаотичного поведения человека на странице"""
    for _ in range(random.randint(3, 6)):
        await page.mouse.wheel(0, random.randint(300, 700))
        await asyncio.sleep(random.uniform(1.0, 2.5))

async def scrape_car_details(context, url):
    page = await context.new_page()
    try:
        # Заходим на страницу конкретной машины
        print(f"🕵️ Заходим в лот: {url}")
        await page.goto(url, wait_until="networkidle", timeout=90000)
        await human_behavior(page) # Листаем страницу, чтобы подгрузить контент

        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')

        # Собираем данные
        title = soup.select_one('h1.entry-title').get_text(strip=True).upper() if soup.select_one('h1.entry-title') else "UNKNOWN MODEL"
        
        # Собираем ВСЕ фото для галереи
        images = []
        for img in soup.find_all('img', src=True):
            src = img['src']
            if 'uploads' in src and 'logo' not in src.lower() and 'icon' not in src.lower():
                images.append(src)
        
        unique_images = list(dict.fromkeys(images)) # Удаляем дубликаты
        main_img = unique_images[0] if unique_images else ""

        # Вытягиваем описание
        desc_element = soup.select_one('.elementor-widget-theme-post-content') or soup.select_one('.entry-content')
        description = desc_element.get_text(separator='\n', strip=True) if desc_element else "Premium Korea Stock"

        car_data = {
            "external_id": url.strip('/').split('/')[-1],
            "brand_model": title,
            "description": description[:1000], # Ограничиваем длину
            "image_url": main_img,
            "source_url": url
        }

        # Сохраняем/Обновляем в базе
        supabase.table("cars").upsert(car_data).execute()
        print(f"✅ Данные лота сохранены: {title}")

    except Exception as e:
        print(f"⚠️ Ошибка при парсинге лота {url}: {e}")
    finally:
        await page.close()

async def run_parser():
    async with async_playwright() as p:
        # Запускаем браузер с расширенными настройками скрытности
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"}
        )
        page = await context.new_page()

        print("🌐 Открываем главную страницу...")
        await page.goto("https://rbautotrade.com/", wait_until="networkidle")
        await asyncio.sleep(random.uniform(3, 5))

        # Вместо клика, который может не сработать, берем ссылки на инвентарь напрямую из кода страницы
        soup = BeautifulSoup(await page.content(), 'html.parser')
        car_links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            # Собираем только ссылки на карточки машин
            if '/inventory/' in href and href.count('/') > 4:
                car_links.append(href)

        links = list(set(car_links))
        print(f"🔎 Найдено уникальных машин: {len(links)}")

        if not links:
            # Если по ссылками не нашли, пробуем зайти в раздел инвентаря
            await page.goto("https://rbautotrade.com/inventory/", wait_until="networkidle")
            await human_behavior(page)
            soup = BeautifulSoup(await page.content(), 'html.parser')
            links = list(set([a['href'] for a in soup.find_all('a', href=True) if '/inventory/' in a['href'] and a['href'].count('/') > 4]))
            print(f"🔎 Повторный поиск дал: {len(links)} машин")

        # Обрабатываем найденные машины
        for link in links[:15]: # Берем первые 15 свежих лотов
            await scrape_car_details(context, link)
            await asyncio.sleep(random.uniform(2, 4)) # Пауза между лотами

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_parser())