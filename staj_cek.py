import requests
from bs4 import BeautifulSoup

def staj_verisini_kaydet():
    url = "https://uib.iku.edu.tr/tr/degisim-programlari/staj-hareketliligi/giden"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    print("Siteye bağlanılıyor...")
    try:
        r = requests.get(url, headers=headers, timeout=10)
        
        if r.status_code == 200:
            soup = BeautifulSoup(r.content, "html.parser")
            
            for element in soup(["nav", "footer", "script", "style", "header"]):
                element.decompose()
            
            metin = soup.get_text(separator='\n', strip=True)
            
            dosya_yolu = "veri_havuzu/erasmus_staj_giden.txt"
            
            with open(dosya_yolu, "w", encoding="utf-8") as f:
                f.write("=== İKÜ GİDEN ÖĞRENCİ STAJ HAREKETLİLİĞİ BİLGİLERİ ===\n\n")
                f.write(metin)
                
            print(f"Veriler başarıyla çekildi ve '{dosya_yolu}' konumuna kaydedildi!")
            
        else:
            print(f"Hata: Sayfaya ulaşılamadı. Durum Kodu: {r.status_code}")
            
    except Exception as e:
        print(f"Bir hata oluştu: {e}")

staj_verisini_kaydet()