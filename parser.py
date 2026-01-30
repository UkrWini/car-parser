import requests
from bs4 import BeautifulSoup
from supabase import create_client
import time

# Твои данные подключения
URL = "https://qenfvaqhbbqmorhvwmxg.supabase.co"
KEY = "sb_secret_JCr9KEjlFpMBO3fymu5l-w_AHPa7qac" 
supabase = create_client(URL, KEY)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
}

def scrape():
    print("🚀 Запуск системного парсера...")
    
    # 1. Получаем список ссылок на машины напрямую из HTML
    try:
        response = requests.get("https://rbautotrade.com/inventory/", headers=HEADERS, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Собираем все ссылки на карточки
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/inventory/' in href and href.count('/') > 4:
                links.append(href)
        
        unique_links = list(set(links))
        print(f"🔎 Найдено машин на сайте: {len(unique_links)}")

        if not unique_links:
            print("❌ Сайт заблокировал доступ. Пробуем запасной метод...")
            return

        for link in unique_links[:15]:
            print(f"🕵️ Обработка: {link}")
            res = requests.get(link, headers=HEADERS, timeout=30)
            car_soup = BeautifulSoup(res.text, 'html.parser')
            
            # Название
            title = car_soup.find('h1').get_text(strip=True).upper() if car_soup.find('h1') else "AUTO KOREA"
            
            # Фото (собираем все картинки из контента)
            images = []
            for img in car_soup.find_all('img', src=True):
                src = img['src']
                if 'uploads' in src and 'logo' not in src.lower():
                    images.append(src)
            
            main_img = images[0] if images else ""
            
            # Описание
            desc_tag = car_soup.select_one('.entry-content') or car_soup.select_one('.elementor-widget-theme-post-content')
            description = desc_tag.get_text(separator=' ', strip=True) if desc_tag else "No description available"

            car_data = {
                "external_id": link.strip('/').split('/')[-1],
                "brand_model": title,
                "description": description[:1000],
                "image_url": main_img,
                "source_url": link
            }

            # Запись в Supabase
            supabase.table("cars").upsert(car_data).execute()
            print(f"✅ Сохранено: {title}")
            time.sleep(1) # Небольшая пауза, чтобы не забанили

    except Exception as e:
        print(f"⚠️ Ошибка: {e}")

if __name__ == "__main__":
    scrape()