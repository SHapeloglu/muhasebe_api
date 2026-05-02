# 📊 Muhasebe API

Flask tabanlı muhasebe uygulamasının tüm tablolarını dışarıya açan **FastAPI** REST katmanı.  
Mevcut Flask uygulamasına (`app.py`) hiç dokunmadan, aynı MySQL veritabanı üzerinde çalışır.

---

## 🗂️ Proje Yapısı

```
muhasebe/
├── app.py          # Mevcut Flask uygulaması (değiştirilmedi)
├── api.py          # ← FastAPI katmanı
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
- Mevcut `config.py` dosyası

### Bağımlılıkları yükle

```bash
pip install fastapi uvicorn sqlalchemy pymysql cryptography pydantic werkzeug
```

### Çalıştır

```bash
# Geliştirme (hot-reload)
uvicorn api:app --reload --port 8000

# Üretim
uvicorn api:app --host 0.0.0.0 --port 8000 --workers 4
```

| Arayüz | URL |
|--------|-----|
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Sağlık | http://localhost:8000/health |

---

## 📡 API Versiyonları

| Versiyon | Prefix | Durum |
|----------|--------|-------|
| v1 | `/api/v1/` | Destekleniyor (geriye dönük uyumlu) |
| v2 | `/api/v2/` | Güncel — yeni özellikler burada |

---

## 🆕 v2 Endpoint'leri

### 🏢 Şirket `/api/v2/sirketler`

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/api/v2/sirketler` | Şirketleri listele |
| GET | `/api/v2/sirketler/{id}` | Tekil şirket |
| POST | `/api/v2/sirketler` | Şirket oluştur |
| PUT | `/api/v2/sirketler/{id}` | Şirket güncelle |
| DELETE | `/api/v2/sirketler/{id}` | Şirketi pasife al |

**Filtreler:** `?aktif=true`

---

### 🏭 Depo `/api/v2/depolar`

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/api/v2/depolar` | Depoları listele |
| GET | `/api/v2/depolar/{id}` | Tekil depo |
| POST | `/api/v2/depolar` | Depo oluştur |
| PUT | `/api/v2/depolar/{id}` | Depo güncelle |
| DELETE | `/api/v2/depolar/{id}` | Depoyu pasife al |

**Filtreler:** `?sirket_id=1&aktif=true`

---

### 🔢 Numara Sıra `/api/v2/numara-siralar`

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/api/v2/numara-siralar` | Serileri listele |
| POST | `/api/v2/numara-siralar` | Yeni seri tanımla |
| GET | `/api/v2/numara-siralar/sonraki` | Sonraki belge no üret |

**Sonraki no örneği:**
```
GET /api/v2/numara-siralar/sonraki?sirket_id=1&belge_tip=FATURA&cari_tip=SATIS
```
```json
{ "belge_no": "FAT2500001", "son_sayi": 1 }
```

---

### 💱 Döviz `/api/v2/dovizler`

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/api/v2/dovizler` | Döviz türlerini listele |
| GET | `/api/v2/dovizler/{id}` | Tekil döviz |
| POST | `/api/v2/dovizler` | Döviz ekle |
| PUT | `/api/v2/dovizler/{id}` | Döviz güncelle |

---

### 🏦 Banka `/api/v2/banka-hesaplari` & `/api/v2/banka-hareketler`

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/api/v2/banka-hesaplari` | Hesapları listele |
| GET | `/api/v2/banka-hesaplari/{id}` | Tekil hesap |
| GET | `/api/v2/banka-hesaplari/{id}/bakiye` | Hesap bakiyesi |
| POST | `/api/v2/banka-hesaplari` | Hesap oluştur |
| PUT | `/api/v2/banka-hesaplari/{id}` | Hesap güncelle |
| DELETE | `/api/v2/banka-hesaplari/{id}` | Hesabı pasife al |
| GET | `/api/v2/banka-hareketler` | Hareketleri listele |
| GET | `/api/v2/banka-hareketler/{id}` | Tekil hareket |
| POST | `/api/v2/banka-hareketler` | Hareket ekle |
| DELETE | `/api/v2/banka-hareketler/{id}` | Hareketi sil |

**Bakiye yanıtı:**
```json
{ "hesap_id": 1, "giris": 50000.00, "cikis": 12000.00, "bakiye": 38000.00 }
```

**Hareket filtreleri:** `?hesap_id=1&yon=GIRIS&tarih_baslangic=2025-01-01`

---

### 💰 Kasa `/api/v2/kasa-hesaplari` & `/api/v2/kasa-hareketler`

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/api/v2/kasa-hesaplari` | Kasaları listele |
| GET | `/api/v2/kasa-hesaplari/{id}/bakiye` | Kasa bakiyesi |
| POST | `/api/v2/kasa-hesaplari` | Kasa oluştur |
| PUT | `/api/v2/kasa-hesaplari/{id}` | Kasa güncelle |
| DELETE | `/api/v2/kasa-hesaplari/{id}` | Kasayı pasife al |
| GET | `/api/v2/kasa-hareketler` | Hareketleri listele |
| POST | `/api/v2/kasa-hareketler` | Hareket ekle |
| DELETE | `/api/v2/kasa-hareketler/{id}` | Hareketi sil |

**Hareket filtreleri:** `?hesap_id=1&yon=CIKIS&tarih_baslangic=2025-01-01`

---

### 📋 Cari Hesap Fişi `/api/v2/cari-fisler`

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/api/v2/cari-fisler` | Fişleri listele |
| GET | `/api/v2/cari-fisler/{id}` | Tekil fiş (satırlarıyla) |
| POST | `/api/v2/cari-fisler` | Fiş oluştur |
| DELETE | `/api/v2/cari-fisler/{id}` | Fişi sil |

**Fiş oluşturma örneği:**
```json
{
  "sirket_id": 1,
  "fisno": "CHF250001",
  "tarih": "2025-04-29",
  "aciklama": "Ay sonu mutabakatı",
  "satirlar": [
    { "cari_id": 1, "hareket_tipi": "BORC", "tutar": 5000.00 },
    { "cari_id": 2, "hareket_tipi": "ALACAK", "tutar": 3000.00 }
  ]
}
```

---

### 📜 Çek / Senet `/api/v2/cek-senetler`

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/api/v2/cek-senetler` | Listele |
| GET | `/api/v2/cek-senetler/{id}` | Tekil kayıt |
| POST | `/api/v2/cek-senetler` | Yeni çek/senet |
| PUT | `/api/v2/cek-senetler/{id}` | Güncelle |
| DELETE | `/api/v2/cek-senetler/{id}` | Sil |

**Filtreler:** `?sirket_id=1&tip=CEK&yon=ALACAK&durum=PORTFOY`

**tip:** `CEK` | `SENET` — **yon:** `ALACAK` | `BORC`

**durum:** `PORTFOY` | `TAHSILDE` | `TAHSIL_EDILDI` | `CIRO_EDILDI` | `PROTESTO` | `IPTAL`

---

### 📅 Taksit Planı `/api/v2/taksitler`

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/api/v2/taksitler` | Taksitleri listele |
| POST | `/api/v2/taksitler` | Taksit ekle |
| PUT | `/api/v2/taksitler/{id}/odendi` | Ödendi olarak işaretle |
| DELETE | `/api/v2/taksitler/{id}` | Taksiti sil |

**Filtreler:** `?belge_id=5&odendi=false`

---

### 📂 Hesap Grubu `/api/v2/hesap-gruplari`

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/api/v2/hesap-gruplari` | Grupları listele |
| GET | `/api/v2/hesap-gruplari/{id}` | Tekil grup |
| POST | `/api/v2/hesap-gruplari` | Grup oluştur |
| PUT | `/api/v2/hesap-gruplari/{id}` | Grubu güncelle |
| DELETE | `/api/v2/hesap-gruplari/{id}` | Grubu pasife al |

**Filtreler:** `?tip=CARI&seviye=1&aktif=true` — **tip:** `CARI` | `STOK`

---

### 📊 Rapor `/api/v2/raporlar`

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/api/v2/raporlar` | Raporları listele |
| GET | `/api/v2/raporlar/{id}` | Tekil rapor |
| POST | `/api/v2/raporlar` | Yeni rapor tanımla |
| DELETE | `/api/v2/raporlar/{id}` | Raporu pasife al |
| GET | `/api/v2/raporlar/{id}/calistir` | SQL sorgusunu çalıştır |

> ⚠️ Sadece `SELECT` sorguları çalışır. `DROP`, `DELETE`, `UPDATE` gibi komutlar reddedilir.

---

### 🗺️ Adres Referansları `/api/v2/adres`

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/api/v2/adres/ulkeler` | Ülkeleri listele |
| GET | `/api/v2/adres/iller` | İlleri listele (`?ulke_id=1`) |
| GET | `/api/v2/adres/ilceler` | İlçeleri listele (`?il_id=34`) |
| GET | `/api/v2/adres/mahalleler` | Mahalleleri listele (`?ilce_id=12`) |

---

### 📮 Cari Adres `/api/v2/cari-adresler`

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/api/v2/cari-adresler` | Adresleri listele |
| POST | `/api/v2/cari-adresler` | Adres ekle |
| PUT | `/api/v2/cari-adresler/{id}` | Adres güncelle |
| DELETE | `/api/v2/cari-adresler/{id}` | Adresi pasife al |

**Filtreler:** `?cari_id=1` — **adres_tipi:** `MERKEZ` | `SUBE` | `FATURA` | `SEVKIYAT` | `DIGER`

---

### 📞 Cari İletişim `/api/v2/cari-iletisimler`

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/api/v2/cari-iletisimler` | İletişimleri listele (`?cari_id=1`) |
| POST | `/api/v2/cari-iletisimler` | İletişim ekle |
| DELETE | `/api/v2/cari-iletisimler/{id}` | İletişimi pasife al |

**tip:** `TELEFON` | `CEP` | `FAX` | `EMAIL` | `WEB` | `DIGER`

---

### 🏦 Cari Banka Hesabı `/api/v2/cari-banka-hesaplari`

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/api/v2/cari-banka-hesaplari` | Hesapları listele (`?cari_id=1`) |
| POST | `/api/v2/cari-banka-hesaplari` | Hesap ekle |
| DELETE | `/api/v2/cari-banka-hesaplari/{id}` | Hesabı pasife al |

---

### 👤 Kullanıcı `/api/v2/kullanicilar`

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/api/v2/kullanicilar` | Kullanıcıları listele |
| GET | `/api/v2/kullanicilar/{id}` | Tekil kullanıcı |
| DELETE | `/api/v2/kullanicilar/{id}` | Kullanıcıyı devre dışı bırak |
| GET | `/api/v2/kullanicilar/{id}/yetkiler` | Kullanıcı yetkileri |

---

### 📈 Dashboard `/api/v2/ozet`

```
GET /api/v2/ozet?sirket_id=1
```
```json
{
  "cari_sayisi": 42,
  "stok_sayisi": 158,
  "sirket_sayisi": 2,
  "acik_fatura": 7,
  "banka_net_bakiye": 125000.00,
  "kasa_net_bakiye": 8500.00,
  "vadesi_gelen_cek": 2
}
```

---

## 📋 v1 Endpoint'leri (Geriye Dönük Uyumlu)

Tüm v1 endpoint'leri çalışmaya devam eder.

| Grup | Prefix |
|------|--------|
| Birim Grubu | `/api/v1/birim-gruplari` |
| Birim | `/api/v1/birimler` |
| Birim Dönüşüm | `/api/v1/birim-donusumleri` |
| Birim Çevirme | `/api/v1/birim-cevirme` |
| Cari | `/api/v1/cariler` |
| Cari Hareket | `/api/v1/cari-hareketler` |
| Stok | `/api/v1/stoklar` |
| Stok Hareket | `/api/v1/stok-hareketler` |
| Belge | `/api/v1/belgeler` |
| Belge Satır | `/api/v1/belge-satirlari` |
| Özet | `/api/v1/ozet` |

---

## 📝 İstek Örnekleri

### Banka hareketi ekle

```bash
curl -X POST http://localhost:8000/api/v2/banka-hareketler \
  -H "Content-Type: application/json" \
  -d '{
    "banka_hesap_id": 1,
    "tarih": "2025-04-29",
    "fisno": "BNK250001",
    "fis_tipi": "TAHSILAT",
    "yon": "GIRIS",
    "tutar": 15000.00,
    "cari_id": 1
  }'
```

### Çek kaydet

```bash
curl -X POST http://localhost:8000/api/v2/cek-senetler \
  -H "Content-Type: application/json" \
  -d '{
    "sirket_id": 1,
    "tip": "CEK",
    "yon": "ALACAK",
    "cari_id": 1,
    "tutar": 25000.00,
    "vade_tarihi": "2025-06-30",
    "durum": "PORTFOY"
  }'
```

### Rapor çalıştır

```bash
curl "http://localhost:8000/api/v2/raporlar/1/calistir"
```

---

## 🔒 Güvenlik Notları

- `allow_origins=["*"]` satırını üretimde kısıtlayın
- JWT / API Key doğrulaması ekleyin
- `config.py` dosyasını `.gitignore`'a ekleyin
- Üretimde `--reload` kullanmayın

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
