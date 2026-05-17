import os
from langchain_community.document_loaders import PyMuPDFLoader, DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

print("Belgeler okunuyor...")
pdf_loader = DirectoryLoader('./veri_havuzu', glob="**/*.pdf", loader_cls=PyMuPDFLoader)
txt_loader = DirectoryLoader('./veri_havuzu', glob="**/*.txt", loader_cls=TextLoader, loader_kwargs={'encoding': 'utf-8'})
json_loader = DirectoryLoader('./veri_havuzu', glob="**/*.json", loader_cls=TextLoader, loader_kwargs={'encoding': 'utf-8'})

pdf_docs = pdf_loader.load()
txt_docs = txt_loader.load()
json_docs = json_loader.load()

tum_belgeler = pdf_docs + txt_docs + json_docs
for doc in tum_belgeler:
    print(f"Okunan dosya: {doc.metadata.get('source')}")

print(f"Toplam {len(tum_belgeler)} sayfa/belge okundu.")

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=2000,
    chunk_overlap=400,
    separators=["\n\n", "\n", " "]
)
parcalar = text_splitter.split_documents(tum_belgeler)
print(f"Belgeler toplam {len(parcalar)} parçaya bölündü.")

print("Veritabanı oluşturuluyor (Bu işlem birkaç dakika sürebilir)...")
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

vectorstore = Chroma.from_documents(
    documents=parcalar,
    embedding=embeddings,
    persist_directory="./chroma_db"
)

print("✅ Bütün veriler başarıyla kaydedildi!")