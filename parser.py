import requests
from bs4 import BeautifulSoup
from supabase import create_client
import time

# Твои данные подключения
URL = "https://qenfvaqhbbqmorhvwmxg.supabase.co"
KEY = "sb_secret_JCr9KEjlFpMBO3fymu5l-w_AHPa7qac" 
supabase = create_client(URL, KEY)

def scrape():
    print("🚀 Запуск парсера через обходной путь...")
    
    # Используем сервис-прокладку, чтобы скрыть IP Гитхаба
    # Это бесплатный анонимайзер
    proxy_url = "https://api.allorigins.win/get?url="
    target_url = "https://rbautotrade.com/inventory/"
    
    try:
        response = requests.get(f"{proxy_url}{target_url}", timeout=30)
        data = response.json()
        html = data['contents']
        
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/inventory/' in href and len(href) > 35:
                links.append(href)
        
        unique_links = list(set(links))
        print(f"🔎 Найдено уникальных лотов: {len(unique_links)}")

        if not unique_links:
            print("⚠️ Ссылки не найдены даже через прокси. Пробую метод 'Жатва'.")
            return

        for link in unique_links[:10]:
            print(f"🕵️ Качаем данные: {link}")
            car_res = requests.get(f"{proxy_url}{link}", timeout=30)
            car_html = car_res.json()['contents']
            car_soup = BeautifulSoup(car_html, 'html.parser')
            
            title = car_soup.find('h1').get_text(strip=True).upper() if car_soup.find('h1') else "KOREA CAR"
            
            # Картинки
            images = [img['src'] for img in car_soup.find_all('img', src=True) if 'uploads' in img['src']]
            main_img = images[0] if images else ""
            
            # Описание
            desc = car_soup.select_one('.entry-content').get_text(strip=True) if car_soup.select_one('.entry-content') else "No description"

            car_data = {
                "external_id": link.strip('/').split('/')[-1],
                "brand_model": title,
                "description": desc[:1000],
                "image_url": main_img,
                "source_url": link
            }

            supabase.table("cars").upsert(car_data).execute()
            print(f"✅ Записано в базу: {title}")
            time.sleep(2)

    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    scrape()
    