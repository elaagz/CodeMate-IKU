import streamlit as st
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI
import requests
from bs4 import BeautifulSoup
import os
import json
import time

LOGO_PATH = "assets/codemate_logo.png"
# SESSION STATE BAŞLATMA 
if "sohbet_havuzu" not in st.session_state:
    st.session_state.sohbet_havuzu = {} 

if "mesajlar" not in st.session_state:
    st.session_state.mesajlar = []

if "chat_id" not in st.session_state:
    st.session_state.chat_id = None

@st.dialog("Sohbet Silinsin mi?")
def sohbet_silme_onayi(file_id):
    st.write(f"Bu sohbet kaydını silmek istediğinize emin misiniz? Bu işlem geri alınamaz.")
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("İptal", use_container_width=True, key=f"cancel_{file_id}"):
            st.rerun()
    with col2:
        if st.button("Sohbeti Sil", type="primary", use_container_width=True, key=f"confirm_{file_id}"):
            # Silme işlemleri
            if file_id in st.session_state.sohbet_havuzu:
                del st.session_state.sohbet_havuzu[file_id]
            
            if st.session_state.get("chat_id") == file_id:
                st.session_state.mesajlar = []
                st.session_state.chat_id = None
                
            st.session_state.silindi_mesaji = "Sohbet başarıyla silindi."
            st.rerun()

@st.dialog("Sistem Sıfırlansın mı?")
def sifirlama_onay_kutusu():
    st.write("Bu işlem, tüm sohbet geçmişinizi ve kullanıcı ayarlarınızı kalıcı olarak silecektir. Emin misiniz?")
    st.markdown("---")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("İptal", use_container_width=True):
            st.rerun()
    with col2:
        if st.button("Sil", type="primary", use_container_width=True):
            if "user_type" in st.session_state:
                del st.session_state.user_type
            st.session_state.mesajlar = []
            st.session_state.sohbet_havuzu = {}
            st.session_state.chat_id = None
            st.rerun()

# SAYFA YAPILANDIRMASI 
load_dotenv()

LOGO_PATH = "assets/codemate_logo.png"

st.set_page_config(
    page_title="CodeMate İKÜ",
    page_icon=LOGO_PATH,
    layout="centered"
)

with open("style.css", "r", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ANA EKRAN BAŞLIKLARI
col_logo, col_title = st.columns([0.08, 0.92])

with col_logo:
    st.image(LOGO_PATH, width=58)

with col_title:
    st.markdown("""
    <h1 class="main-title" style="margin: 0; margin-left: -13px; padding-top: 5px; line-height: 1;">CodeMate İKÜ</h1>
    """, unsafe_allow_html=True)
st.caption("Bilgisayar Programcılığı bölümü hakkında her şeyi bana sorabilirsin!")
st.markdown("---")

# BİLDİRİM ALANI
if "silindi_mesaji" in st.session_state:
    st.toast(st.session_state.silindi_mesaji, icon="🗑️")
    del st.session_state.silindi_mesaji

# KLASÖR VE SOHBET AYARLARI
CHAT_SAVES_DIR = "sohbet_gecmisi"
if not os.path.exists(CHAT_SAVES_DIR):
    os.makedirs(CHAT_SAVES_DIR)

def sohbeti_kaydet():
    if "mesajlar" in st.session_state and len(st.session_state.mesajlar) > 0:
        if "chat_id" not in st.session_state or st.session_state.chat_id is None:
            st.session_state.chat_id = str(int(time.time()))
        
        baslik = st.session_state.mesajlar[0]["icerik"][:20] + "..."
        st.session_state.sohbet_havuzu[st.session_state.chat_id] = {
            "baslik": baslik,
            "mesajlar": st.session_state.mesajlar
        }     

def yeni_sohbet_baslat():
    st.session_state.mesajlar = []
    st.session_state.chat_id = str(int(time.time()))
    st.rerun()

# SIDEBAR
with st.sidebar:
    col1, col2, col3 = st.columns([0.7, 3, 0.7])

    with col2:
        st.image(LOGO_PATH, width=200)
    
    if st.button("➕ Yeni Sohbet Başlat", use_container_width=True):
        yeni_sohbet_baslat()
    
    st.subheader("Eski Sohbetlerin")

    # Klasör yerine kullanıcının kendi tarayıcı hafızasından okuyoruz
    for file_id, sohbet_verisi in sorted(st.session_state.sohbet_havuzu.items(), reverse=True):
        baslik = sohbet_verisi["baslik"]
        col_chat, col_del = st.columns([0.82, 0.18], gap="small")
        
        with col_chat:
            if st.button(f"💬 {baslik}", key=f"load_{file_id}", use_container_width=True):
                st.session_state.mesajlar = sohbet_verisi["mesajlar"]
                st.session_state.chat_id = file_id
                st.rerun()
        
        with col_del:
            if st.button("🗑️", key=f"btn_del_{file_id}", use_container_width=True):
                if file_id in st.session_state.sohbet_havuzu:
                    del st.session_state.sohbet_havuzu[file_id]
                if st.session_state.get("chat_id") == file_id:
                    st.session_state.mesajlar = []
                    st.session_state.chat_id = None
                st.session_state.silindi_mesaji = "Sohbet başarıyla silindi."
                st.rerun()
    

    if "user_type" in st.session_state:
        st.markdown("---")

        if st.button("🔄 Rolü Değiştir", use_container_width=True, help="Öğrenci/Aday seçim ekranına döner"):
            del st.session_state.user_type
            
            st.rerun()

        if st.button("🗑️ Sistemi Sıfırla", use_container_width=True):
            sifirlama_onay_kutusu()

        st.markdown(f"""
        <div class="fixed-user-box">
            <span class="fixed-user-icon">👤</span>
            <div>
                <b>Kullanıcı Modu:</b> {st.session_state.user_type}
            </div>
        </div>
        """, unsafe_allow_html=True)

# UNICAL
def unical_motoru():
    url = "https://www.iku.edu.tr/unical"
    UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        r = requests.get(url, headers=UA, timeout=10)
        if r.status_code != 200: return ""
        
        soup = BeautifulSoup(r.content, "html.parser")
        
        for element in soup(["nav", "footer", "script", "style", "header"]):
            element.decompose()
            
        metin = soup.get_text(separator=' | ', strip=True)
        
        return metin[:25000]
    except:
        return ""
    
# SİSTEMİ VE HAFIZAYI YÜKLEME
@st.cache_resource(show_spinner=False)
def sistemi_hazirla():
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    vectorstore = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash", 
        temperature=0.1,
        max_retries=3,
        timeout=30
    )
    return llm, vectorstore

try:
    llm, vectorstore = sistemi_hazirla()
except Exception as e:
    st.error(f"Sistem başlatılamadı. Hata: {e}")
    st.stop()

# SOHBET GEÇMİŞİ YÖNETİMİ
if "mesajlar" not in st.session_state:
    st.session_state.mesajlar = []

    # KULLANICI TİPİ KONTROLÜ VE SEÇİM EKRANI
if "user_type" not in st.session_state:
        st.markdown("### Hoş Geldin! 👋 \nSana daha iyi yardımcı olabilmem için lütfen durumunu seçer misin?")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("💻 Bilgisayar Programcılığı Öğrencisiyim", use_container_width=True, key="main_ogrenci"):
                st.session_state.user_type = "Bölüm Öğrencisi"
                st.session_state.mesajlar = [{
                    "rol": "assistant", 
                    "icerik": "Selam!👋 İKÜ Bilgisayar Programcılığı asistanın burada. Ne sormak istersin?"
                }]
                st.rerun()
                
        with col2:
            if st.button("🌟 Aday Öğrenciyim", use_container_width=True, key="main_aday"):
                st.session_state.user_type = "Aday Öğrenci"
                st.session_state.mesajlar = [{
                    "rol": "assistant", 
                    "icerik": "Hoş geldin! Bilgisayar Programcılığı bölümüne olan ilgin harika. 🚀 Merak ettiğin her şeyi sorabilirsin."
                }]
                st.rerun()
        st.stop()

for mesaj in st.session_state.mesajlar:
    with st.chat_message(mesaj["rol"]):
        st.markdown(mesaj["icerik"])

#  KULLANICI ETKİLEŞİMİ VE RAG SİSTEMİ
if soru := st.chat_input("Sorunuzu buraya yazın..."):
    st.session_state.mesajlar.append({"rol": "user", "icerik": soru})

    if "chat_id" not in st.session_state or st.session_state.chat_id is None:
        st.session_state.chat_id = str(int(time.time()))

    with st.chat_message("user"):
        st.markdown(soru)

    with st.chat_message("assistant"):
        cevap_metni = ""
        temiz_soru = soru.lower().strip()
        
        gunluk_sohbet = ["selam", "merhaba", "hey", "selamlar", "naber", "merhabalar","slm"]
        
        if temiz_soru in gunluk_sohbet or temiz_soru.startswith(("selam", "merhaba")):
            cevap_metni = "Merhaba! Ben İKÜ Bilgisayar Programcılığı asistanıyım. Sana bölüm, dersler veya etkinlikler hakkında nasıl yardımcı olabilirim?"
            st.markdown(cevap_metni)
            st.session_state.mesajlar.append({"rol": "assistant", "icerik": cevap_metni})
            sohbeti_kaydet()
            st.rerun()
        else:
            with st.spinner("Yanıtlanıyor..."):
                try:
                    arama_sorusu = soru.lower().replace("mail", "e-posta").replace("oda", "ofis").replace("dönem", "yarıyıl")

                    if len(st.session_state.mesajlar) >= 3:
                        onceki_soru = st.session_state.mesajlar[-3]["icerik"].lower()
                        arama_sorusu = f"{onceki_soru} {arama_sorusu}"
                    
                    docs = vectorstore.similarity_search(arama_sorusu, k=25) 
                    context = "\n\n".join([f"KAYNAK: {doc.metadata.get('source', 'bilinmiyor')}\n{doc.page_content}" for doc in docs])

                    etkinlik_sorgusu = any(k in temiz_soru for k in ["takvim", "unical", "güncel duyuru", "bu haftaki"])

                    if etkinlik_sorgusu or (st.session_state.user_type == "Bölüm Öğrencisi" and "etkinlik" in temiz_soru):
                        canli_veriler = unical_motoru()
                        if canli_veriler:
                            context = f"=== CANLI UNICAL TAKVİM VERİLERİ ===\n{canli_veriler}\n\n" + context

                    gecmis = ""
                    if len(st.session_state.mesajlar) > 1:
                        for m in st.session_state.mesajlar[:-1]: 
                            gecmis += f"{m['rol'].upper()}: {m['icerik']}\n"

                    if not context.strip():
                        cevap_metni = "Belgelerimde bu konuyla ilgili net bir bilgi bulamadım."
                    else:
                        if st.session_state.user_type == "Aday Öğrenci":
                            ozel_talimat = "Üslubun tanıtım odaklı, samimi ve ikna edici olmalı."
                        else:
                            ozel_talimat = "Üslubun profesyonel, teknik ve doğrudan çözüm odaklı olmalı."
                        
                        prompt_sablonu = f"""
                        Sen İstanbul Kültür Üniversitesi (İKÜ) Bilgisayar Programcılığı bölümü için geliştirilmiş öğrenci dostu bir asistansın. 
                        Şu an konuştuğun kişi: {st.session_state.user_type}
                        Özel Talimat: {ozel_talimat}

                        1. BİLGİ KAYNAĞI: Aşağıdaki BAĞLAM'daki bilgileri titizlikle incele. Yurtlar, kampüs imkanları veya UniCAL gibi konularda bilgi varsa mutlaka paylaş. Bilgi bağlamda yoksa uydurma ama "sadece şu konularda yardımcı olabilirim" diyerek kendini kısıtlama.
                        2. GENEL REHBERLİK: Aşağıdaki BAĞLAM'da yer alan bilgiler ister bölümle ilgili olsun, ister yurt, konaklama veya sosyal etkinliklerle ilgili olsun; kullanıcıya mutlaka yardımcı ol. 
                        3. BAĞLAM KULLANIMI: Bilgiyi SADECE aşağıdaki BAĞLAM'dan al. Eğer yurtlar, ücretler veya kayıt süreciyle ilgili veri bağlamda mevcutsa "bilmiyorum" deme, o veriyi kullanarak cevap ver.
                        4. NİYET OKUMA: Sohbet geçmişine bakarak konuyu anla. Kullanıcı "oda" diyorsa "ofis" aradığını, "dönem" diyorsa "yarıyıl" aradığını anla.
                        5. EKSİKSİZ LİSTELEME: Kullanıcı bir dönemin derslerini listelemeni isterse, BAĞLAMDA o döneme ait geçen TÜM DERSLERİ (ortak dersler dahil) hiçbirini atlamadan alt alta yaz. Sadece dersin adını ve kredisini yaz. KESİN KURAL: Başka dönemin derslerini bu listeye KESİNLİKLE karıştırma!
                        6. DERS DETAYI: Kullanıcı liste DEĞİL DE, tek bir dersin İÇERİĞİNİ sorarsa (Örn: "Veri Yapıları nasıl bir ders?"), SADECE o zaman o dersin hocasını, notlandırmasını ve tüyolarını madde madde uzun uzun yaz.
                        7. SPESİFİK SORULAR: "Staj kaç gün?", "Ofisi nerede?" gibi net sorularda lafı uzatma, tek cümleyle cevap ver. (Staj için sigorta gününü değil, mezuniyet için zorunlu iş gününü baz al).
                        8. ÜSLUP: Samimi ve net ol.Ancak kullanıcı sana doğrudan "selam", "merhaba" demedikçe cevaplarına KESİNLİKLE "Merhaba", "Selam", "Hoş geldin" gibi kelimelerle BAŞLAMA. Sohbet zaten devam ediyor, lafı hiç uzatmadan doğrudan konuya gir ve soruyu yanıtla.
                        9. KİŞİSELLEŞTİRİLMİŞ TAVSİYE SİSTEMİ : 
                        - ETKİNLİKLER İÇİN: Kullanıcı okuldaki etkinlikleri sorduğunda, var olan tüm etkinlikleri listele. Ancak listede "Yazılım, Yapay Zeka, Bilgisayar, Bilişim, Teknoloji, Kodlama veya Doğal Dil İşleme" gibi Bilgisayar Programcılığı bölümünü doğrudan ilgilendiren etkinlikler varsa, bunları sıradan bir madde gibi sunma! Cevabın en sonunda "💡 Asistan Tavsiyesi:" başlığı açarak bu etkinliği, "Bölümün dolayısıyla, kariyerin için özellikle bu etkinliğe katılmanı şiddetle tavsiye ederim!" şeklinde özellikle vurgula.
                        - KULÜPLER İÇİN: Kullanıcı kulüpleri sorduğunda veya genel bir tavsiye istediğinde; Bilgisayar Programcılığı bölümü için teknik kulüpleri mutlaka "💡 Bölümüne Özel Kulüp Tavsiyesi:" başlığıyla en öne çıkar. "Bir Bilgisayar Programcılığı öğrencisi olarak teknik network kurman ve projeler geliştirmen için bu kulüp ideal!" şeklinde bir motivasyon cümlesi ekle.
                        10. BÖLÜM ETKİNLİĞİ ÖNCELİĞİ: Kullanıcı "bölümdeki etkinlikler" diye sorduğunda, ÖNCE BAĞLAM (context) içindeki dökümanları tara. Eğer dökümanlarda Bilgisayar Programcılığı bölümüne özel bir seminer, teknik gezi veya proje sunumu varsa BUNLARI "Bölüm Etkinlikleri" başlığı altında ver.
                        11. GENEL OKUL ETKİNLİKLERİ (UniCAL): UniCAL'den gelen canlı veriler tüm üniversiteyi kapsar. Kullanıcı spesifik olarak bölümü sorduğunda, UniCAL listesindeki her şeyi dökme! Sadece "Yazılım, Yapay Zeka, Bilgisayar, Bilişim, Kodlama, Algoritma" gibi anahtar kelimeleri içerenleri bölümle ilişkilendirerek sun.
    
                        SOHBET GEÇMİŞİ:
                        {gecmis}

                        BAĞLAM:
                        {context}

                        SORU: {soru}
                        """

                        mesaj_alani = st.empty()
                        cevap_metni = ""

                        for parca in llm.stream(prompt_sablonu):
                            icerik = parca.content
                            
                            for i in range(0, len(icerik), 4):
                                cevap_metni += icerik[i:i+4]
                                mesaj_alani.markdown(cevap_metni)
                                
                                time.sleep(0.008)

                    st.session_state.mesajlar.append({"rol": "assistant", "icerik": cevap_metni})
                    sohbeti_kaydet()
                    st.rerun()

                except Exception as e:
                    if "429" in str(e):
                        st.warning("⚠️ Yoğunluk var, 15 saniye bekleyip tekrar dener misin?")
                    else:
                        st.error(f"Sistemde bir sorun oluştu: {e}")
