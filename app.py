import streamlit as st
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI
import requests
from bs4 import BeautifulSoup
import os
import time
import hashlib
from supabase import create_client, Client
import extra_streamlit_components as stx

LOGO_PATH = "assets/codemate_logo.png"

# SAYFA YAPILANDIRMASI 
load_dotenv()

st.set_page_config(
    page_title="CodeMate İKÜ",
    page_icon=LOGO_PATH,
    layout="centered"
)

# SUPABASE BAĞLANTISI
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Lütfen .env dosyasında SUPABASE_URL ve SUPABASE_KEY değerlerini tanımlayın.")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

# KULLANICI VERİTABANI İŞLEMLERİ 
def kullanici_kaydet(username, password, user_type):
    try:
        password_hash = hash_password(password)
        response = supabase.table("kullanicilar").insert({
            "username": username,
            "password_hash": password_hash,
            "user_type": user_type
        }).execute()
        return True, "Kayıt başarılı!"
    except Exception as e:
        if "duplicate key" in str(e) or "kullanicilar_username_key" in str(e):
            return False, "Bu kullanıcı adı zaten alınmış."
        return False, f"Hata: {e}"

def kullanici_giris(username, password):
    try:
        password_hash = hash_password(password)
        response = supabase.table("kullanicilar").select("*").eq("username", username).execute()
        if len(response.data) == 0:
            return False, "Kullanıcı bulunamadı.", None
        
        user = response.data[0]
        if user["password_hash"] == password_hash:
            return True, "Giriş başarılı!", user
        else:
            return False, "Hatalı şifre.", None
    except Exception as e:
        return False, f"Hata: {e}", None

# --- SOHBET VERİTABANI İŞLEMLERİ ---
def sohbeti_kaydet():
    if "mesajlar" in st.session_state and len(st.session_state.mesajlar) > 0 and st.session_state.get("logged_in"):
        if "chat_id" not in st.session_state or st.session_state.chat_id is None:
            st.session_state.chat_id = str(int(time.time()))
        
        ilk_mesaj = st.session_state.mesajlar[0]["icerik"]
        baslik = ilk_mesaj[:20] + "..." if len(ilk_mesaj) > 20 else ilk_mesaj
        
        try:
            supabase.table("sohbetler").upsert({
                "id": st.session_state.chat_id,
                "user_id": st.session_state.user["id"],
                "title": baslik,
                "messages": st.session_state.mesajlar
            }).execute()
        except Exception as e:
            pass

def sohbeti_sil(chat_id):
    try:
        supabase.table("sohbetler").delete().eq("id", chat_id).execute()
        if st.session_state.get("chat_id") == chat_id:
            st.session_state.mesajlar = []
            st.session_state.chat_id = None
        return True
    except Exception as e:
        return False

def eski_sohbetleri_getir(user_id):
    try:
        response = supabase.table("sohbetler").select("id", "title").eq("user_id", user_id).order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        return []

def yeni_sohbet_baslat():
    st.session_state.mesajlar = []
    st.session_state.chat_id = str(int(time.time()))
    st.rerun()

@st.dialog("Sohbet Silinsin mi?")
def sohbet_silme_onayi(chat_id):
    st.write("Bu sohbet kaydını silmek istediğinize emin misiniz? Bu işlem geri alınamaz.")
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("İptal", use_container_width=True, key=f"cancel_{chat_id}"):
            st.rerun()
    with col2:
        if st.button("Sohbeti Sil", type="primary", use_container_width=True, key=f"confirm_{chat_id}"):
            if sohbeti_sil(chat_id):
                st.session_state.silindi_mesaji = "Sohbet başarıyla silindi."
            else:
                st.session_state.silindi_mesaji = "Sohbet silinirken bir hata oluştu."
            st.rerun()

@st.dialog("Tüm Sohbet Geçmişi Sıfırlansın mı?")
def sifirlama_onay_kutusu():
    st.write("Tüm sohbet geçmişiniz kalıcı olarak silinecektir. Emin misiniz?")
    st.markdown("---")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("İptal", use_container_width=True):
            st.rerun()
    with col2:
        if st.button("Sıfırla", type="primary", use_container_width=True):
            try:
                supabase.table("sohbetler").delete().eq("user_id", st.session_state.user["id"]).execute()
                st.session_state.mesajlar = []
                st.session_state.chat_id = None
                st.session_state.silindi_mesaji = "Tüm sohbet geçmişiniz başarıyla silindi."
            except Exception as e:
                st.session_state.silindi_mesaji = f"Sıfırlanırken hata oluştu: {e}"
            st.rerun()

try:
    with open("style.css", "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except Exception as e:
    pass

# COOKIE YÖNETİCİSİ TANIMLAMA
cookie_manager = stx.CookieManager(key="cookie_manager")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "logout_clicked" not in st.session_state:
    st.session_state.logout_clicked = False
if "run_count" not in st.session_state:
    st.session_state.run_count = 0
else:
    st.session_state.run_count += 1

saved_user_id = cookie_manager.get(cookie="user_id")
if not saved_user_id:
    st.session_state.logout_clicked = False
if not st.session_state.logged_in and not st.session_state.logout_clicked:
    try:
        if saved_user_id and saved_user_id != "" and saved_user_id != "None":
            response = supabase.table("kullanicilar").select("*").eq("id", int(saved_user_id)).execute()
            if response.data:
                user_data = response.data[0]
                st.session_state.logged_in = True
                st.session_state.user = user_data
                st.session_state.user_type = user_data["user_type"]
                st.session_state.mesajlar = []
                st.session_state.ilk_giris = True
                st.rerun()
    except Exception as e:
        pass

# GİRİŞ / KAYIT EKRANI 
if not st.session_state.logged_in:
    if st.session_state.run_count == 0 and not saved_user_id:
        time.sleep(0.8)
        st.rerun()
    col_space1, col_form, col_space2 = st.columns([0.15, 0.7, 0.15])
    
    with col_form:
        c1, c2, c3 = st.columns([1, 1.2, 1])
        with c2:
            st.image(LOGO_PATH, use_container_width=True)
            
        st.markdown("""
            <div class="login-title-container">
                <div class="login-gradient-title">CodeMate İKÜ</div>
                <div class="login-subtitle">Yapay Zeka Destekli Bilgisayar Programcılığı Asistanı</div>
            </div>
        """, unsafe_allow_html=True)
        
        sekme_giris, sekme_kayit = st.tabs(["Giriş Yap", "Kayıt Ol"])
        
        with sekme_giris:
            with st.form("form_giris"):
                kullanici_adi = st.text_input("Kullanıcı Adı / Öğrenci No", key="login_username").strip()
                sifre = st.text_input("Şifre", type="password", key="login_password")
                btn_giris = st.form_submit_button("Giriş Yap", use_container_width=True)
                
                if btn_giris:
                    if not kullanici_adi or not sifre:
                        st.warning("⚠️ Lütfen tüm alanları doldurun.")
                    else:
                        basarili, mesaj, user_data = kullanici_giris(kullanici_adi, sifre)
                        if basarili:
                            st.session_state.logged_in = True
                            st.session_state.user = user_data
                            st.session_state.user_type = user_data["user_type"]
                            st.session_state.mesajlar = []
                            
                            try:
                                cookie_manager.set(cookie="user_id", val=str(user_data["id"]), key="login_cookie_set")
                            except:
                                pass
                                
                            st.success("Başarıyla giriş yapıldı!")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error(f"❌ {mesaj}")
                            
        with sekme_kayit:
            with st.form("form_kayit"):
                yeni_kullanici = st.text_input("Kullanıcı Adı / Öğrenci No", key="reg_username").strip()
                yeni_sifre = st.text_input("Şifre", type="password", key="reg_password")
                tip = st.selectbox("Durumunuz", ["Bölüm Öğrencisi", "Aday Öğrenci"], key="reg_usertype")
                btn_kayit = st.form_submit_button("Hesap Oluştur ve Kaydol", use_container_width=True)
                
                if btn_kayit:
                    if not yeni_kullanici or not yeni_sifre:
                        st.warning("⚠️ Lütfen tüm alanları doldurun.")
                    elif len(yeni_sifre) < 6:
                        st.warning("⚠️ Şifre en az 6 karakter olmalıdır.")
                    else:
                        basarili, mesaj = kullanici_kaydet(yeni_kullanici, yeni_sifre, tip)
                        if basarili:
                            st.success("Hesabınız başarıyla oluşturuldu! Şimdi Giriş Yap sekmesinden giriş yapabilirsiniz.")
                        else:
                            st.error(f"❌ {mesaj}")
    st.stop()
# GİRİŞ YAPILDIĞINDA
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

# SIDEBAR
with st.sidebar:
    col1, col2, col3 = st.columns([0.7, 3, 0.7])

    with col2:
        st.image(LOGO_PATH, width=200)
    
    if st.button("➕ Yeni Sohbet Başlat", use_container_width=True):
        yeni_sohbet_baslat()
    
    st.subheader("Eski Sohbetlerin")
    
    saved_chats = eski_sohbetleri_getir(st.session_state.user["id"])

    for chat in saved_chats:
        file_id = chat["id"]
        baslik = chat["title"]
        col_chat, col_del = st.columns([0.82, 0.18], gap="small")
        
        with col_chat:
            if st.button(f"💬 {baslik}", key=f"load_{file_id}", use_container_width=True):
                try:
                    response = supabase.table("sohbetler").select("messages").eq("id", file_id).execute()
                    if response.data:
                        st.session_state.mesajlar = response.data[0]["messages"]
                        st.session_state.chat_id = file_id
                        st.rerun()
                except Exception as e:
                    st.error("Sohbet yüklenemedi.")
            
        with col_del:
            if st.button("🗑️", key=f"btn_del_{file_id}", use_container_width=True):
                sohbet_silme_onayi(file_id)

    st.markdown("---")

    if st.button("Çıkış Yap", use_container_width=True):
        try:
            cookie_manager.set(cookie="user_id", val="", key="logout_cookie_clear")
        except:
            pass
        st.session_state.logout_clicked = True
        st.session_state.logged_in = False
        st.session_state.user = None
        st.session_state.user_type = None
        st.session_state.mesajlar = []

    if st.button("Geçmişi Sil", use_container_width=True):
        sifirlama_onay_kutusu()

    st.markdown(f"""
    <div class="fixed-user-box">
        <span class="fixed-user-icon">👤</span>
        <div>
            <b>Kullanıcı Modu:</b> {st.session_state.user_type}<br>
            <b>Kullanıcı:</b> {st.session_state.user['username']}
        </div>
    </div>
    """, unsafe_allow_html=True)

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

if len(st.session_state.mesajlar) == 0 and st.session_state.get("ilk_giris", False):
    if st.session_state.user_type == "Bölüm Öğrencisi":
        st.session_state.mesajlar = [{
            "rol": "assistant", 
            "icerik": "Selam!👋 İKÜ Bilgisayar Programcılığı asistanın burada. Ne sormak istersin?"
        }]
    else:
        st.session_state.mesajlar = [{
            "rol": "assistant", 
            "icerik": "Hoş geldin! Bilgisayar Programcılığı bölümüne olan ilgin harika. 🚀 Merak ettiğin her şeyi sorabilirsin."
        }]
    st.session_state.ilk_giris = False

for mesaj in st.session_state.mesajlar:
    with st.chat_message(mesaj["rol"]):
        st.markdown(mesaj["icerik"])

# KULLANICI ETKİLEŞİMİ VE RAG SİSTEMİ
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
                        for m in st.session_state.mesajlar[-8:-1]: 
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
                        - BÖLÜM ETKİNLİĞİ ÖNCELİĞİ: Kullanıcı "bölümdeki etkinlikler" diye sorduğunda, ÖNCE BAĞLAM (context) içindeki dökümanları tara. Eğer dökümanlarda Bilgisayar Programcılığı bölümüne özel bir seminer, teknik gezi veya proje sunumu varsa BUNLARI "Bölüm Etkinlikleri" başlığı altında ver.
                        - GENEL OKUL ETKİNLİKLERİ (UniCAL): UniCAL'den gelen canlı veriler tüm üniversiteyi kapsar. Kullanıcı spesifik olarak bölümü sorduğunda, UniCAL listesindeki her şeyi dökme! Sadece "Yazılım, Yapay Zeka, Bilgisayar, Bilişim, Kodlama, Algoritma" gibi anahtar kelimeleri içerenleri bölümle ilişkilendirerek sun.
                        - ERASMUS VE HAREKETLİLİK KESİN AYRIM KURALI: Kullanıcı doğrudan veya dolaylı olarak "Erasmus", "yurt dışı", "Avrupa imkanları" gibi sorular sorduğunda, cevabına KESİNLİKLE VE İSTİSNAZIZ şu cümleyle başla: "İstanbul Kültür Üniversitesi Bilgisayar Programcılığı programı kapsamında anlaşmalı bir partner üniversitemiz bulunmamaktadır. Bu nedenle, bölüm öğrencileri Erasmus+ Öğrenim Hareketliliğinden yararlanamamaktadır." Bu olumsuz durumu belirttikten sonra, hemen bir alt satıra geç ve şu alternatifi sun: "Ancak, öğrenciler dilerse Erasmus+ Staj Hareketliliği programından faydalanabilirler." Bu iki kavramın farkını net koy; 'Öğrenim' (Avrupa'da bir okulda ders görme) YOKTUR, 'Staj' (Avrupa'da bir şirkette zorunlu staj yapma) VARDIR. Bilgileri birbirine karıştırma.
            
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
