import requests
from bs4 import BeautifulSoup
from supabase import create_client
import time
import random

# Твои данные
URL = "https://qenfvaqhbbqmorhvwmxg.supabase.co"
KEY = "sb_secret_JCr9KEjlFpMBO3fymu5l-w_AHPa7qac" 
supabase = create_client(URL, KEY)

def get_session():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://google.com"
    })
    return session

def scrape():
    s = get_session()
    print("🚀 Попытка обхода блокировки...")
    
    try:
        # 1. Заходим сначала на главную, чтобы получить куки
        s.get("https://rbautotrade.com/", timeout=20)
        time.sleep(random.randint(2, 4))
        
        # 2. Идем в инвентарь
        response = s.get("https://rbautotrade.com/inventory/", timeout=20)
        print(f"📡 Статус сайта: {response.status_code}")
        
        if response.status_code != 200:
            print("❌ Сайт всё еще блокирует. Нужен другой метод.")
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        links = [a['href'] for a in soup.find_all('a', href=True) if '/inventory/' in a['href'] and len(a['href']) > 35]
        unique_links = list(set(links))
        
        print(f"🔎 Найдено машин: {len(unique_links)}")

        for link in unique_links[:10]:
            print(f"🕵️ Обработка: {link}")
            res = s.get(link, timeout=20)
            car_soup = BeautifulSoup(res.text, 'html.parser')
            
            title = car_soup.find('h1').get_text(strip=True) if car_soup.find('h1') else "AUTO KOREA"
            
            # Собираем фото
            imgs = [img['src'] for img in car_soup.find_all('img', src=True) if 'uploads' in img['src'] and 'logo' not in img['src'].lower()]
            main_img = imgs[0] if imgs else ""
            
            # Описание
            desc = car_soup.select_one('.entry-content').get_text(strip=True) if car_soup.select_one('.entry-content') else ""

            data = {
                "external_id": link.strip('/').split('/')[-1],
                "brand_model": title.upper(),
                "description": desc[:1000],
                "image_url": main_img,
                "source_url": link
            }

            supabase.table("cars").upsert(data).execute()
            print(f"✅ Сохранено: {title}")
            time.sleep(random.randint(2, 5))

    except Exception as e:
        print(f"⚠️ Ошибка: {e}")

if __name__ == "__main__":
    scrape()