import requests
from bs4 import BeautifulSoup
from supabase import create_client
import time

# Данные подключения
URL = "https://qenfvaqhbbqmorhvwmxg.supabase.co"
KEY = "sb_secret_JCr9KEjlFpMBO3fymu5l-w_AHPa7qac" 
supabase = create_client(URL, KEY)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
}

def scrape():
    print("🚀 Старт глубокого парсинга...")
    try:
        # 1. Пробуем загрузить страницу инвентаря
        response = requests.get("https://rbautotrade.com/inventory/", headers=HEADERS, timeout=30)
        print(f"📡 Статус ответа сайта: {response.status_code}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Собираем ВСЕ ссылки, которые содержат слово 'inventory'
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            # Фильтруем: ссылка должна быть длинной (значит это лот) и не быть самой страницей инвентаря
            if '/inventory/' in href and len(href) > 35:
                links.append(href)
        
        unique_links = list(set(links))
        print(f"🔎 Найдено потенциальных лотов: {len(unique_links)}")

        if not unique_links:
            print("❌ Ссылок не найдено. Возможно, структура сайта изменилась или доступ заблокирован.")
            # Для теста: выведем часть HTML, чтобы понять что видит бот
            print("DEBUG: Первые 500 символов страницы:", response.text[:500])
            return

        for link in unique_links[:15]:
            try:
                print(f"🕵️ Парсим лот: {link}")
                res = requests.get(link, headers=HEADERS, timeout=30)
                car_soup = BeautifulSoup(res.text, 'html.parser')
                
                # Заголовок
                title = "Unknown Car"
                h1 = car_soup.find('h1')
                if h1:
                    title = h1.get_text(strip=True).upper()
                
                # Фото
                images = []
                for img in car_soup.find_all('img', src=True):
                    src = img['src']
                    if 'uploads' in src and 'logo' not in src.lower() and 'thumb' not in src.lower():
                        images.append(src)
                
                main_img = images[0] if images else ""
                
                # Описание
                desc_tag = car_soup.select_one('.entry-content') or car_soup.select_one('.elementor-widget-theme-post-content')
                description = desc_tag.get_text(separator=' ', strip=True) if desc_tag else "No description"

                car_data = {
                    "external_id": link.strip('/').split('/')[-1],
                    "brand_model": title,
                    "description": description[:1000],
                    "image_url": main_img,
                    "source_url": link
                }

                # ЗАПИСЬ В БАЗУ
                result = supabase.table("cars").upsert(car_data).execute()
                print(f"✅ Сохранено в Supabase: {title}")
                
            except Exception as car_e:
                print(f"⚠️ Ошибка на лоте {link}: {car_e}")
            
            time.sleep(2) # Задержка между запросами

    except Exception as e:
        print(f"💥 Критическая ошибка: {e}")

if __name__ == "__main__":
    scrape()