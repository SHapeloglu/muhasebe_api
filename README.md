# 📊 Muhasebe API

Flask tabanlı muhasebe uygulamasının tüm tablolarını dışarıya açan **FastAPI** REST katmanı.  
Mevcut Flask uygulamasına (`app.py`) hiç dokunmadan, aynı MySQL veritabanı üzerinde çalışır.

---

## 🗂️ Proje Yapısı

```
muhasebe/
├── app.py          # Mevcut Flask uygulaması (değiştirilmedi)
├── api.py          # ← FastAPI katmanı (yeni)
├── config.py       # Veritabanı bağlantı ayarları
├── requirements.txt
└── templates/
    └── ...
```

---

## ⚙️ Kurulum

### Gereksinimler

- Python 3.10+
- MySQL 8.0+
- Mevcut `config.py` dosyası (veritabanı bağlantısı)

### Bağımlılıkları yükle

```bash
pip install fastapi uvicorn sqlalchemy pymysql cryptography pydantic
```

> Flask bağımlılıkları zaten kuruluysa sadece `fastapi` ve `uvicorn` eklemeniz yeterlidir.

### Çalıştır

```bash
# Geliştirme (hot-reload ile)
uvicorn api:app --reload --port 8000

# Üretim
uvicorn api:app --host 0.0.0.0 --port 8000 --workers 4
```

### Swagger UI

```
http://localhost:8000/docs
```

### ReDoc

```
http://localhost:8000/redoc
```

---

## 📡 API Endpoint'leri

### Genel

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/health` | Veritabanı sağlık kontrolü |
| GET | `/api/v1/ozet` | Dashboard istatistikleri |

---

### 📦 Birim Grubu `/api/v1/birim-gruplari`

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/api/v1/birim-gruplari` | Tüm birim gruplarını listele |
| GET | `/api/v1/birim-gruplari/{id}` | Tekil birim grubu getir |
| POST | `/api/v1/birim-gruplari` | Yeni birim grubu oluştur |
| PUT | `/api/v1/birim-gruplari/{id}` | Birim grubunu güncelle |
| DELETE | `/api/v1/birim-gruplari/{id}` | Birim grubunu pasife al |

**Filtreler:** `?aktif=true`

---

### 📏 Birim `/api/v1/birimler`

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/api/v1/birimler` | Birimleri listele |
| GET | `/api/v1/birimler/{id}` | Tekil birim getir |
| POST | `/api/v1/birimler` | Yeni birim oluştur |
| PUT | `/api/v1/birimler/{id}` | Birimi güncelle |
| DELETE | `/api/v1/birimler/{id}` | Birimi pasife al |
| GET | `/api/v1/birim-cevirme` | Birimler arası miktar çevirme |

**Filtreler:** `?grup_id=1&aktif=true`

**Birim çevirme örneği:**
```
GET /api/v1/birim-cevirme?kaynak_id=1&hedef_id=2&miktar=5
```
```json
{
  "ok": true,
  "katsayi": 100.0,
  "sonuc": 500.0
}
```

---

### 🔄 Birim Dönüşüm `/api/v1/birim-donusumleri`

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/api/v1/birim-donusumleri` | Dönüşümleri listele |
| GET | `/api/v1/birim-donusumleri/{id}` | Tekil dönüşüm getir |
| POST | `/api/v1/birim-donusumleri` | Yeni dönüşüm tanımla |
| PUT | `/api/v1/birim-donusumleri/{id}` | Dönüşümü güncelle |
| DELETE | `/api/v1/birim-donusumleri/{id}` | Dönüşümü pasife al |

**Filtreler:** `?aktif=true`

---

### 👤 Cari `/api/v1/cariler`

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/api/v1/cariler` | Carileri listele |
| GET | `/api/v1/cariler/{id}` | Tekil cari getir |
| GET | `/api/v1/cariler/{id}/bakiye` | Cari borç/alacak/bakiye |
| POST | `/api/v1/cariler` | Yeni cari oluştur |
| PUT | `/api/v1/cariler/{id}` | Cariyi güncelle |
| DELETE | `/api/v1/cariler/{id}` | Cariyi pasife al |

**Filtreler:** `?tip=ALICI&aktif=true&sehir=İstanbul`

**tip değerleri:** `ALICI` | `SATICI` | `HER_IKISI`

**Bakiye örneği:**
```json
{
  "cari_id": 1,
  "borc": 15000.00,
  "alacak": 5000.00,
  "bakiye": 10000.00
}
```

---

### 💰 Cari Hareket `/api/v1/cari-hareketler`

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/api/v1/cari-hareketler` | Hareketleri listele |
| GET | `/api/v1/cari-hareketler/{id}` | Tekil hareket getir |
| POST | `/api/v1/cari-hareketler` | Yeni hareket ekle |
| DELETE | `/api/v1/cari-hareketler/{id}` | Hareketi sil |

**Filtreler:** `?cari_id=1&hareket_tipi=BORC&tarih_baslangic=2025-01-01&tarih_bitis=2025-12-31`

---

### 🏷️ Stok `/api/v1/stoklar`

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/api/v1/stoklar` | Stok kartlarını listele |
| GET | `/api/v1/stoklar/{id}` | Tekil stok kartı getir |
| GET | `/api/v1/stoklar/{id}/miktar` | Anlık stok miktarı |
| POST | `/api/v1/stoklar` | Yeni stok kartı oluştur |
| PUT | `/api/v1/stoklar/{id}` | Stok kartını güncelle |
| DELETE | `/api/v1/stoklar/{id}` | Stok kartını pasife al |

**Filtreler:** `?tip=MALZEME&aktif=true`

**tip değerleri:** `MALZEME` | `HIZMET`

---

### 📦 Stok Hareket `/api/v1/stok-hareketler`

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/api/v1/stok-hareketler` | Hareketleri listele |
| GET | `/api/v1/stok-hareketler/{id}` | Tekil hareket getir |
| POST | `/api/v1/stok-hareketler` | Yeni hareket ekle |
| DELETE | `/api/v1/stok-hareketler/{id}` | Hareketi sil |

**Filtreler:** `?stok_id=1&hareket_tipi=GIRIS&tarih_baslangic=2025-01-01`

---

### 🧾 Belge `/api/v1/belgeler`

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/api/v1/belgeler` | Belgeleri listele (satırlarıyla birlikte) |
| GET | `/api/v1/belgeler/{id}` | Tekil belge getir (satırlarıyla birlikte) |
| POST | `/api/v1/belgeler` | Yeni belge oluştur |
| PUT | `/api/v1/belgeler/{id}` | Belgeyi güncelle |
| DELETE | `/api/v1/belgeler/{id}` | Belgeyi sil |

**Filtreler:** `?belge_tip=FATURA&cari_tip=SATIS&durum=ACIK&cari_id=1&limit=50`

**belge_tip değerleri:** `TALEP` | `SIPARIS` | `IRSALIYE` | `FATURA`

**durum değerleri:** `ACIK` | `ONAYLANDI` | `IPTAL`

---

### 📝 Belge Satır `/api/v1/belge-satirlari`

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/api/v1/belge-satirlari` | Satırları listele |
| GET | `/api/v1/belge-satirlari/{id}` | Tekil satır getir |

**Filtreler:** `?baslik_id=5&stok_id=2`

> Satır eklemek/silmek için belge endpoint'ini (`POST /api/v1/belgeler`) kullanın — satırlar belgeyle birlikte gönderilir.

---

## 📝 İstek / Yanıt Örnekleri

### Yeni Cari Oluştur

```bash
curl -X POST http://localhost:8000/api/v1/cariler \
  -H "Content-Type: application/json" \
  -d '{
    "kod": "C00010",
    "unvan": "Örnek Firma A.Ş.",
    "tip": "ALICI",
    "vergi_no": "1234567890",
    "vergi_dairesi": "Karşıyaka",
    "telefon": "0232 555 0000",
    "email": "info@ornek.com",
    "sehir": "İzmir"
  }'
```

### Fatura Oluştur (Satırlarıyla)

```bash
curl -X POST http://localhost:8000/api/v1/belgeler \
  -H "Content-Type: application/json" \
  -d '{
    "belge_tip": "FATURA",
    "belge_no": "FAT2500001",
    "tarih": "2025-04-29",
    "cari_id": 1,
    "cari_tip": "SATIS",
    "durum": "ACIK",
    "satirlar": [
      {
        "sira_no": 1,
        "stok_id": 1,
        "aciklama": "Alüminyum Profil",
        "miktar": 10,
        "birim_id": 2,
        "birim_fiyat": 85.50,
        "iskonto_oran": 0,
        "kdv_orani": 20,
        "kdvsiz_tutar": 855.00,
        "kdv_tutar": 171.00,
        "kdvli_tutar": 1026.00
      }
    ]
  }'
```

### Stok Miktarı Sorgula

```bash
curl http://localhost:8000/api/v1/stoklar/1/miktar
```

```json
{
  "stok_id": 1,
  "tip": "MALZEME",
  "miktar": 47.5
}
```

---

## 🔒 Güvenlik Notları

> Üretim ortamına geçmeden önce aşağıdakileri yapın:

- `api.py` içindeki `allow_origins=["*"]` ayarını kısıtlayın:
  ```python
  allow_origins=["https://sizin-domain.com"]
  ```
- API anahtarı / JWT doğrulaması ekleyin (FastAPI `Security` modülü önerilir)
- `config.py` dosyasını `.gitignore`'a ekleyin, şifreler repoya girmesin
- Üretimde `--reload` flag'ini kullanmayın

---

## 🛠️ Teknolojiler

| Katman | Teknoloji |
|--------|-----------|
| API Framework | [FastAPI](https://fastapi.tiangolo.com/) |
| ASGI Sunucu | [Uvicorn](https://www.uvicorn.org/) |
| ORM | [SQLAlchemy](https://www.sqlalchemy.org/) |
| Şema Doğrulama | [Pydantic v2](https://docs.pydantic.dev/) |
| Veritabanı | MySQL 8.0+ |
| MySQL Sürücü | [PyMySQL](https://pymysql.readthedocs.io/) |
| Web Arayüzü | Flask (mevcut, değiştirilmedi) |

---

## 📄 Lisans

MIT
