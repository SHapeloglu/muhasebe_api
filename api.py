"""
Muhasebe FastAPI Katmanı
========================
Mevcut Flask uygulamasındaki tüm SQLAlchemy modellerini
FastAPI üzerinden REST API olarak dışarıya açar.

Tablolar:
  • birim_grubu      → /api/v1/birim-gruplari
  • birim            → /api/v1/birimler
  • birim_donusum    → /api/v1/birim-donusumleri
  • cari             → /api/v1/cariler
  • cari_hareket     → /api/v1/cari-hareketler
  • stok_karti       → /api/v1/stoklar
  • stok_hareket     → /api/v1/stok-hareketler
  • belge_baslik     → /api/v1/belgeler
  • belge_satir      → /api/v1/belge-satirlari

Kurulum:
  pip install fastapi uvicorn sqlalchemy pymysql cryptography pydantic

Çalıştırma:
  uvicorn api:app --reload --port 8000
  veya: python api.py
"""

from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from enum import Enum as PyEnum

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Numeric, \
    Date, DateTime, Text, SmallInteger, ForeignKey, Enum, func, Index, \
    UniqueConstraint
from sqlalchemy.orm import declarative_base, Session, sessionmaker, relationship

# ════════════════════════════════════════════════════════════
#  VERİTABANI BAĞLANTISI
# ════════════════════════════════════════════════════════════

try:
    import config as cfg
    MYSQL_URI = (
        f"mysql+pymysql://{cfg.DB_USER}:{cfg.DB_PASSWORD}"
        f"@{cfg.DB_HOST}:{cfg.DB_PORT}/{cfg.DB_NAME}?charset=utf8mb4"
    )
    engine_kwargs = dict(
        pool_size=cfg.POOL_SIZE,
        max_overflow=cfg.MAX_OVERFLOW,
        pool_timeout=cfg.POOL_TIMEOUT,
        pool_recycle=cfg.POOL_RECYCLE,
        pool_pre_ping=cfg.POOL_PRE_PING,
    )
except ImportError:
    import os
    MYSQL_URI = os.environ.get(
        "DATABASE_URL",
        "mysql+pymysql://root:sifrenizi_buraya_yazin@localhost:3306/muhasebe?charset=utf8mb4",
    )
    engine_kwargs = {"pool_pre_ping": True, "pool_recycle": 1800}

engine = create_engine(MYSQL_URI, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ════════════════════════════════════════════════════════════
#  SQLALCHEMY MODELLERİ  (app.py ile birebir aynı)
# ════════════════════════════════════════════════════════════

class BirimGrubu(Base):
    __tablename__ = "birim_grubu"
    id       = Column(Integer, primary_key=True, autoincrement=True)
    ad       = Column(String(50), unique=True, nullable=False)
    aciklama = Column(String(200))
    aktif    = Column(Boolean, default=True, nullable=False)
    birimler = relationship("Birim", backref="grup", lazy="dynamic",
                             foreign_keys="Birim.grup_id")


class Birim(Base):
    __tablename__ = "birim"
    id       = Column(Integer, primary_key=True, autoincrement=True)
    grup_id  = Column(Integer, ForeignKey("birim_grubu.id", ondelete="RESTRICT"), nullable=False)
    kod      = Column(String(20), unique=True, nullable=False)
    ad       = Column(String(50), nullable=False)
    katsayi  = Column(Numeric(20, 10), nullable=False, default=1.0)
    taban_mi = Column(Boolean, default=False, nullable=False)
    aktif    = Column(Boolean, default=True, nullable=False)
    __table_args__ = (Index("ix_birim_grup", "grup_id"),)


class BirimDonusum(Base):
    __tablename__ = "birim_donusum"
    id              = Column(Integer, primary_key=True, autoincrement=True)
    kaynak_birim_id = Column(Integer, ForeignKey("birim.id", ondelete="CASCADE"), nullable=False)
    hedef_birim_id  = Column(Integer, ForeignKey("birim.id", ondelete="CASCADE"), nullable=False)
    carpan          = Column(Numeric(20, 10), nullable=False)
    aciklama        = Column(String(200))
    aktif           = Column(Boolean, default=True, nullable=False)
    __table_args__ = (
        UniqueConstraint("kaynak_birim_id", "hedef_birim_id", name="uq_donusum_kh"),
        Index("ix_donusum_kaynak", "kaynak_birim_id"),
    )


class Cari(Base):
    __tablename__ = "cari"
    id               = Column(Integer, primary_key=True, autoincrement=True)
    kod              = Column(String(20), unique=True, nullable=False)
    unvan            = Column(String(200), nullable=False)
    tip              = Column(Enum("ALICI", "SATICI", "HER_IKISI"), nullable=False)
    vergi_no         = Column(String(20))
    vergi_dairesi    = Column(String(100))
    telefon          = Column(String(20))
    email            = Column(String(100))
    adres            = Column(Text)
    sehir            = Column(String(50))
    aktif            = Column(Boolean, default=True, nullable=False)
    olusturma_tarihi = Column(DateTime, default=datetime.now)


class CariHareket(Base):
    __tablename__ = "cari_hareket"
    id           = Column(Integer, primary_key=True, autoincrement=True)
    cari_id      = Column(Integer, ForeignKey("cari.id", ondelete="CASCADE"), nullable=False)
    tarih        = Column(Date, nullable=False, default=date.today)
    belge_no     = Column(String(50))
    aciklama     = Column(String(500))
    hareket_tipi = Column(Enum("BORC", "ALACAK"), nullable=False)
    tutar        = Column(Numeric(15, 2), nullable=False)
    kaynak_tip   = Column(String(20))
    kaynak_id    = Column(Integer)
    __table_args__ = (Index("ix_ch_cari_tarih", "cari_id", "tarih"),)


class StokKarti(Base):
    __tablename__ = "stok_karti"
    id               = Column(Integer, primary_key=True, autoincrement=True)
    kod              = Column(String(50), unique=True, nullable=False)
    ad               = Column(String(200), nullable=False)
    tip              = Column(Enum("MALZEME", "HIZMET"), nullable=False)
    birim_id         = Column(Integer, ForeignKey("birim.id", ondelete="RESTRICT"), nullable=False)
    kdv_orani        = Column(Numeric(5, 2), default=20.00)
    satis_fiyati     = Column(Numeric(15, 4), default=0.0)
    alis_fiyati      = Column(Numeric(15, 4), default=0.0)
    aciklama         = Column(Text)
    aktif            = Column(Boolean, default=True, nullable=False)
    olusturma_tarihi = Column(DateTime, default=datetime.now)


class StokHareket(Base):
    __tablename__ = "stok_hareket"
    id              = Column(Integer, primary_key=True, autoincrement=True)
    stok_id         = Column(Integer, ForeignKey("stok_karti.id", ondelete="CASCADE"), nullable=False)
    tarih           = Column(Date, nullable=False, default=date.today)
    belge_no        = Column(String(50))
    hareket_tipi    = Column(Enum("GIRIS", "CIKIS"), nullable=False)
    birim_id        = Column(Integer, ForeignKey("birim.id", ondelete="RESTRICT"))
    miktar          = Column(Numeric(15, 4), nullable=False)
    cevrilen_miktar = Column(Numeric(15, 4))
    birim_fiyat     = Column(Numeric(15, 4))
    aciklama        = Column(String(500))
    __table_args__ = (Index("ix_sh_stok_tarih", "stok_id", "tarih"),)


class BelgeBaslik(Base):
    __tablename__ = "belge_baslik"
    id               = Column(Integer, primary_key=True, autoincrement=True)
    belge_tip        = Column(Enum("TALEP", "SIPARIS", "IRSALIYE", "FATURA"), nullable=False)
    belge_no         = Column(String(50), unique=True, nullable=False)
    tarih            = Column(Date, nullable=False, default=date.today)
    vade_tarihi      = Column(Date)
    cari_id          = Column(Integer, ForeignKey("cari.id", ondelete="SET NULL"))
    cari_tip         = Column(Enum("SATIS", "ALIS"), nullable=False, default="SATIS")
    aciklama         = Column(Text)
    durum            = Column(Enum("ACIK", "ONAYLANDI", "IPTAL"), default="ACIK")
    kaynak_belge_id  = Column(Integer, ForeignKey("belge_baslik.id", ondelete="SET NULL"))
    toplam_kdvsiz    = Column(Numeric(15, 2), default=0.00)
    toplam_kdv       = Column(Numeric(15, 2), default=0.00)
    toplam_kdvli     = Column(Numeric(15, 2), default=0.00)
    olusturma_tarihi = Column(DateTime, default=datetime.now)
    satirlar         = relationship("BelgeSatir", backref="baslik",
                                    cascade="all, delete-orphan",
                                    order_by="BelgeSatir.sira_no")
    __table_args__ = (
        Index("ix_bb_tip_ctip_tarih", "belge_tip", "cari_tip", "tarih"),
        Index("ix_bb_cari", "cari_id"),
    )


class BelgeSatir(Base):
    __tablename__ = "belge_satir"
    id           = Column(Integer, primary_key=True, autoincrement=True)
    baslik_id    = Column(Integer, ForeignKey("belge_baslik.id", ondelete="CASCADE"), nullable=False)
    sira_no      = Column(SmallInteger, nullable=False)
    stok_id      = Column(Integer, ForeignKey("stok_karti.id", ondelete="SET NULL"))
    aciklama     = Column(String(500))
    miktar       = Column(Numeric(15, 4), nullable=False, default=1.0)
    birim_id     = Column(Integer, ForeignKey("birim.id", ondelete="RESTRICT"))
    birim_fiyat  = Column(Numeric(15, 4), nullable=False, default=0.0)
    iskonto_oran = Column(Numeric(5, 2), default=0.00)
    kdv_orani    = Column(Numeric(5, 2), default=20.00)
    kdvsiz_tutar = Column(Numeric(15, 2), default=0.00)
    kdv_tutar    = Column(Numeric(15, 2), default=0.00)
    kdvli_tutar  = Column(Numeric(15, 2), default=0.00)
    __table_args__ = (Index("ix_bs_baslik", "baslik_id"),)


# ════════════════════════════════════════════════════════════
#  PYDANTIC ŞEMALARI
# ════════════════════════════════════════════════════════════

# ── Yardımcı ────────────────────────────────────────────────
def d(v) -> Optional[float]:
    """Decimal → float dönüşümü (None güvenli)."""
    return float(v) if v is not None else None


# ── BirimGrubu ───────────────────────────────────────────────
class BirimGrubuCreate(BaseModel):
    ad: str
    aciklama: Optional[str] = None
    aktif: bool = True

class BirimGrubuRead(BirimGrubuCreate):
    id: int
    class Config:
        from_attributes = True


# ── Birim ────────────────────────────────────────────────────
class BirimCreate(BaseModel):
    grup_id: int
    kod: str
    ad: str
    katsayi: float = 1.0
    taban_mi: bool = False
    aktif: bool = True

class BirimRead(BirimCreate):
    id: int
    class Config:
        from_attributes = True


# ── BirimDonusum ─────────────────────────────────────────────
class BirimDonusumCreate(BaseModel):
    kaynak_birim_id: int
    hedef_birim_id: int
    carpan: float
    aciklama: Optional[str] = None
    aktif: bool = True

class BirimDonusumRead(BirimDonusumCreate):
    id: int
    class Config:
        from_attributes = True


# ── Cari ─────────────────────────────────────────────────────
class CariTip(str, PyEnum):
    ALICI     = "ALICI"
    SATICI    = "SATICI"
    HER_IKISI = "HER_IKISI"

class CariCreate(BaseModel):
    kod: str
    unvan: str
    tip: CariTip
    vergi_no: Optional[str] = None
    vergi_dairesi: Optional[str] = None
    telefon: Optional[str] = None
    email: Optional[str] = None
    adres: Optional[str] = None
    sehir: Optional[str] = None
    aktif: bool = True

class CariRead(CariCreate):
    id: int
    olusturma_tarihi: Optional[datetime] = None
    class Config:
        from_attributes = True


# ── CariHareket ──────────────────────────────────────────────
class HareketTipiCari(str, PyEnum):
    BORC   = "BORC"
    ALACAK = "ALACAK"

class CariHareketCreate(BaseModel):
    cari_id: int
    tarih: date
    belge_no: Optional[str] = None
    aciklama: Optional[str] = None
    hareket_tipi: HareketTipiCari
    tutar: float
    kaynak_tip: Optional[str] = None
    kaynak_id: Optional[int] = None

class CariHareketRead(CariHareketCreate):
    id: int
    class Config:
        from_attributes = True


# ── StokKarti ────────────────────────────────────────────────
class StokTip(str, PyEnum):
    MALZEME = "MALZEME"
    HIZMET  = "HIZMET"

class StokKartiCreate(BaseModel):
    kod: str
    ad: str
    tip: StokTip
    birim_id: int
    kdv_orani: float = 20.0
    satis_fiyati: float = 0.0
    alis_fiyati: float = 0.0
    aciklama: Optional[str] = None
    aktif: bool = True

class StokKartiRead(StokKartiCreate):
    id: int
    olusturma_tarihi: Optional[datetime] = None
    class Config:
        from_attributes = True


# ── StokHareket ──────────────────────────────────────────────
class HareketTipiStok(str, PyEnum):
    GIRIS = "GIRIS"
    CIKIS = "CIKIS"

class StokHareketCreate(BaseModel):
    stok_id: int
    tarih: date
    belge_no: Optional[str] = None
    hareket_tipi: HareketTipiStok
    birim_id: Optional[int] = None
    miktar: float
    cevrilen_miktar: Optional[float] = None
    birim_fiyat: Optional[float] = None
    aciklama: Optional[str] = None

class StokHareketRead(StokHareketCreate):
    id: int
    class Config:
        from_attributes = True


# ── BelgeSatir ───────────────────────────────────────────────
class BelgeSatirCreate(BaseModel):
    sira_no: int
    stok_id: Optional[int] = None
    aciklama: Optional[str] = None
    miktar: float = 1.0
    birim_id: Optional[int] = None
    birim_fiyat: float = 0.0
    iskonto_oran: float = 0.0
    kdv_orani: float = 20.0
    kdvsiz_tutar: float = 0.0
    kdv_tutar: float = 0.0
    kdvli_tutar: float = 0.0

class BelgeSatirRead(BelgeSatirCreate):
    id: int
    baslik_id: int
    class Config:
        from_attributes = True


# ── BelgeBaslik ──────────────────────────────────────────────
class BelgeTip(str, PyEnum):
    TALEP    = "TALEP"
    SIPARIS  = "SIPARIS"
    IRSALIYE = "IRSALIYE"
    FATURA   = "FATURA"

class CariTipBelge(str, PyEnum):
    SATIS = "SATIS"
    ALIS  = "ALIS"

class BelgeDurum(str, PyEnum):
    ACIK      = "ACIK"
    ONAYLANDI = "ONAYLANDI"
    IPTAL     = "IPTAL"

class BelgeBaslikCreate(BaseModel):
    belge_tip: BelgeTip
    belge_no: str
    tarih: date
    vade_tarihi: Optional[date] = None
    cari_id: Optional[int] = None
    cari_tip: CariTipBelge = CariTipBelge.SATIS
    aciklama: Optional[str] = None
    durum: BelgeDurum = BelgeDurum.ACIK
    kaynak_belge_id: Optional[int] = None
    toplam_kdvsiz: float = 0.0
    toplam_kdv: float = 0.0
    toplam_kdvli: float = 0.0
    satirlar: List[BelgeSatirCreate] = []

class BelgeBaslikRead(BaseModel):
    id: int
    belge_tip: str
    belge_no: str
    tarih: date
    vade_tarihi: Optional[date] = None
    cari_id: Optional[int] = None
    cari_tip: str
    aciklama: Optional[str] = None
    durum: str
    kaynak_belge_id: Optional[int] = None
    toplam_kdvsiz: Optional[float] = None
    toplam_kdv: Optional[float] = None
    toplam_kdvli: Optional[float] = None
    olusturma_tarihi: Optional[datetime] = None
    satirlar: List[BelgeSatirRead] = []

    @classmethod
    def from_orm_obj(cls, obj: BelgeBaslik) -> "BelgeBaslikRead":
        return cls(
            id=obj.id,
            belge_tip=obj.belge_tip,
            belge_no=obj.belge_no,
            tarih=obj.tarih,
            vade_tarihi=obj.vade_tarihi,
            cari_id=obj.cari_id,
            cari_tip=obj.cari_tip,
            aciklama=obj.aciklama,
            durum=obj.durum,
            kaynak_belge_id=obj.kaynak_belge_id,
            toplam_kdvsiz=d(obj.toplam_kdvsiz),
            toplam_kdv=d(obj.toplam_kdv),
            toplam_kdvli=d(obj.toplam_kdvli),
            olusturma_tarihi=obj.olusturma_tarihi,
            satirlar=[BelgeSatirRead.model_validate(s) for s in obj.satirlar],
        )


# ════════════════════════════════════════════════════════════
#  FASTAPI UYGULAMASI
# ════════════════════════════════════════════════════════════

app = FastAPI(
    title="Muhasebe API",
    description="Muhasebe programının tüm tablolarına REST erişimi",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Üretimde kısıtlayın!
    allow_methods=["*"],
    allow_headers=["*"],
)


# ════════════════════════════════════════════════════════════
#  GENEL
# ════════════════════════════════════════════════════════════

@app.get("/health", tags=["Genel"])
def health(db: Session = Depends(get_db)):
    from sqlalchemy import text
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "mysql", "time": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@app.get("/api/v1/ozet", tags=["Genel"])
def ozet(db: Session = Depends(get_db)):
    """Ana sayfa istatistikleri."""
    return {
        "cari_sayisi":  db.query(func.count(Cari.id)).filter(Cari.aktif.is_(True)).scalar(),
        "stok_sayisi":  db.query(func.count(StokKarti.id)).filter(StokKarti.aktif.is_(True)).scalar(),
        "birim_sayisi": db.query(func.count(Birim.id)).filter(Birim.aktif.is_(True)).scalar(),
        "acik_fatura":  db.query(func.count(BelgeBaslik.id)).filter_by(belge_tip="FATURA", durum="ACIK").scalar(),
        "acik_siparis": db.query(func.count(BelgeBaslik.id)).filter_by(belge_tip="SIPARIS", durum="ACIK").scalar(),
    }


# ════════════════════════════════════════════════════════════
#  BİRİM GRUBU  /api/v1/birim-gruplari
# ════════════════════════════════════════════════════════════

@app.get("/api/v1/birim-gruplari", response_model=List[BirimGrubuRead], tags=["Birim Grubu"])
def birim_gruplari_listele(
    aktif: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    q = db.query(BirimGrubu)
    if aktif is not None:
        q = q.filter(BirimGrubu.aktif == aktif)
    return q.order_by(BirimGrubu.ad).all()


@app.get("/api/v1/birim-gruplari/{id}", response_model=BirimGrubuRead, tags=["Birim Grubu"])
def birim_grubu_getir(id: int, db: Session = Depends(get_db)):
    obj = db.get(BirimGrubu, id)
    if not obj:
        raise HTTPException(404, "Birim grubu bulunamadı")
    return obj


@app.post("/api/v1/birim-gruplari", response_model=BirimGrubuRead, status_code=201, tags=["Birim Grubu"])
def birim_grubu_olustur(payload: BirimGrubuCreate, db: Session = Depends(get_db)):
    obj = BirimGrubu(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj


@app.put("/api/v1/birim-gruplari/{id}", response_model=BirimGrubuRead, tags=["Birim Grubu"])
def birim_grubu_guncelle(id: int, payload: BirimGrubuCreate, db: Session = Depends(get_db)):
    obj = db.get(BirimGrubu, id)
    if not obj:
        raise HTTPException(404, "Birim grubu bulunamadı")
    for k, v in payload.model_dump().items():
        setattr(obj, k, v)
    db.commit(); db.refresh(obj)
    return obj


@app.delete("/api/v1/birim-gruplari/{id}", tags=["Birim Grubu"])
def birim_grubu_sil(id: int, db: Session = Depends(get_db)):
    obj = db.get(BirimGrubu, id)
    if not obj:
        raise HTTPException(404, "Birim grubu bulunamadı")
    obj.aktif = False; db.commit()
    return {"ok": True, "mesaj": "Birim grubu pasife alındı"}


# ════════════════════════════════════════════════════════════
#  BİRİM  /api/v1/birimler
# ════════════════════════════════════════════════════════════

@app.get("/api/v1/birimler", response_model=List[BirimRead], tags=["Birim"])
def birimler_listele(
    grup_id: Optional[int] = Query(None),
    aktif: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    q = db.query(Birim)
    if grup_id is not None:
        q = q.filter(Birim.grup_id == grup_id)
    if aktif is not None:
        q = q.filter(Birim.aktif == aktif)
    return q.order_by(Birim.kod).all()


@app.get("/api/v1/birimler/{id}", response_model=BirimRead, tags=["Birim"])
def birim_getir(id: int, db: Session = Depends(get_db)):
    obj = db.get(Birim, id)
    if not obj:
        raise HTTPException(404, "Birim bulunamadı")
    return obj


@app.post("/api/v1/birimler", response_model=BirimRead, status_code=201, tags=["Birim"])
def birim_olustur(payload: BirimCreate, db: Session = Depends(get_db)):
    obj = Birim(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj


@app.put("/api/v1/birimler/{id}", response_model=BirimRead, tags=["Birim"])
def birim_guncelle(id: int, payload: BirimCreate, db: Session = Depends(get_db)):
    obj = db.get(Birim, id)
    if not obj:
        raise HTTPException(404, "Birim bulunamadı")
    for k, v in payload.model_dump().items():
        setattr(obj, k, v)
    db.commit(); db.refresh(obj)
    return obj


@app.delete("/api/v1/birimler/{id}", tags=["Birim"])
def birim_sil(id: int, db: Session = Depends(get_db)):
    obj = db.get(Birim, id)
    if not obj:
        raise HTTPException(404, "Birim bulunamadı")
    obj.aktif = False; db.commit()
    return {"ok": True, "mesaj": "Birim pasife alındı"}


# ════════════════════════════════════════════════════════════
#  BİRİM DÖNÜŞÜM  /api/v1/birim-donusumleri
# ════════════════════════════════════════════════════════════

@app.get("/api/v1/birim-donusumleri", response_model=List[BirimDonusumRead], tags=["Birim Dönüşüm"])
def donusumler_listele(
    aktif: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    q = db.query(BirimDonusum)
    if aktif is not None:
        q = q.filter(BirimDonusum.aktif == aktif)
    return q.all()


@app.get("/api/v1/birim-donusumleri/{id}", response_model=BirimDonusumRead, tags=["Birim Dönüşüm"])
def donusum_getir(id: int, db: Session = Depends(get_db)):
    obj = db.get(BirimDonusum, id)
    if not obj:
        raise HTTPException(404, "Dönüşüm kaydı bulunamadı")
    return obj


@app.post("/api/v1/birim-donusumleri", response_model=BirimDonusumRead, status_code=201, tags=["Birim Dönüşüm"])
def donusum_olustur(payload: BirimDonusumCreate, db: Session = Depends(get_db)):
    obj = BirimDonusum(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj


@app.put("/api/v1/birim-donusumleri/{id}", response_model=BirimDonusumRead, tags=["Birim Dönüşüm"])
def donusum_guncelle(id: int, payload: BirimDonusumCreate, db: Session = Depends(get_db)):
    obj = db.get(BirimDonusum, id)
    if not obj:
        raise HTTPException(404, "Dönüşüm kaydı bulunamadı")
    for k, v in payload.model_dump().items():
        setattr(obj, k, v)
    db.commit(); db.refresh(obj)
    return obj


@app.delete("/api/v1/birim-donusumleri/{id}", tags=["Birim Dönüşüm"])
def donusum_sil(id: int, db: Session = Depends(get_db)):
    obj = db.get(BirimDonusum, id)
    if not obj:
        raise HTTPException(404, "Dönüşüm kaydı bulunamadı")
    obj.aktif = False; db.commit()
    return {"ok": True, "mesaj": "Dönüşüm pasife alındı"}


@app.get("/api/v1/birim-cevirme", tags=["Birim Dönüşüm"])
def birim_cevirme(
    kaynak_id: int,
    hedef_id: int,
    miktar: float = 1.0,
    db: Session = Depends(get_db)
):
    """Birimler arası miktar çevirme."""
    if kaynak_id == hedef_id:
        return {"ok": True, "katsayi": 1.0, "sonuc": round(miktar, 6)}

    kaynak = db.get(Birim, kaynak_id)
    hedef  = db.get(Birim, hedef_id)
    if not kaynak or not hedef:
        raise HTTPException(404, "Birim bulunamadı")

    ozel = db.query(BirimDonusum).filter_by(
        kaynak_birim_id=kaynak_id, hedef_birim_id=hedef_id, aktif=True).first()
    if ozel:
        k = float(ozel.carpan)
        return {"ok": True, "katsayi": k, "sonuc": round(miktar * k, 6)}

    ters = db.query(BirimDonusum).filter_by(
        kaynak_birim_id=hedef_id, hedef_birim_id=kaynak_id, aktif=True).first()
    if ters:
        k = 1.0 / float(ters.carpan)
        return {"ok": True, "katsayi": k, "sonuc": round(miktar * k, 6)}

    if kaynak.grup_id == hedef.grup_id:
        k = float(kaynak.katsayi) / float(hedef.katsayi)
        return {"ok": True, "katsayi": k, "sonuc": round(miktar * k, 6)}

    raise HTTPException(422, "Bu birimler arasında çevrim tanımlı değil")


# ════════════════════════════════════════════════════════════
#  CARİ  /api/v1/cariler
# ════════════════════════════════════════════════════════════

@app.get("/api/v1/cariler", response_model=List[CariRead], tags=["Cari"])
def cariler_listele(
    tip: Optional[str] = Query(None, description="ALICI | SATICI | HER_IKISI"),
    aktif: Optional[bool] = Query(None),
    sehir: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    q = db.query(Cari)
    if aktif is not None:
        q = q.filter(Cari.aktif == aktif)
    if tip:
        q = q.filter(Cari.tip.in_([tip, "HER_IKISI"]))
    if sehir:
        q = q.filter(Cari.sehir.ilike(f"%{sehir}%"))
    return q.order_by(Cari.unvan).all()


@app.get("/api/v1/cariler/{id}", response_model=CariRead, tags=["Cari"])
def cari_getir(id: int, db: Session = Depends(get_db)):
    obj = db.get(Cari, id)
    if not obj:
        raise HTTPException(404, "Cari bulunamadı")
    return obj


@app.get("/api/v1/cariler/{id}/bakiye", tags=["Cari"])
def cari_bakiye(id: int, db: Session = Depends(get_db)):
    if not db.get(Cari, id):
        raise HTTPException(404, "Cari bulunamadı")
    borc = db.query(func.sum(CariHareket.tutar)).filter(
        CariHareket.cari_id == id, CariHareket.hareket_tipi == "BORC").scalar() or 0
    alacak = db.query(func.sum(CariHareket.tutar)).filter(
        CariHareket.cari_id == id, CariHareket.hareket_tipi == "ALACAK").scalar() or 0
    bakiye = float(borc) - float(alacak)
    return {"cari_id": id, "borc": float(borc), "alacak": float(alacak), "bakiye": bakiye}


@app.post("/api/v1/cariler", response_model=CariRead, status_code=201, tags=["Cari"])
def cari_olustur(payload: CariCreate, db: Session = Depends(get_db)):
    obj = Cari(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj


@app.put("/api/v1/cariler/{id}", response_model=CariRead, tags=["Cari"])
def cari_guncelle(id: int, payload: CariCreate, db: Session = Depends(get_db)):
    obj = db.get(Cari, id)
    if not obj:
        raise HTTPException(404, "Cari bulunamadı")
    for k, v in payload.model_dump().items():
        setattr(obj, k, v)
    db.commit(); db.refresh(obj)
    return obj


@app.delete("/api/v1/cariler/{id}", tags=["Cari"])
def cari_sil(id: int, db: Session = Depends(get_db)):
    obj = db.get(Cari, id)
    if not obj:
        raise HTTPException(404, "Cari bulunamadı")
    obj.aktif = False; db.commit()
    return {"ok": True, "mesaj": "Cari pasife alındı"}


# ════════════════════════════════════════════════════════════
#  CARİ HAREKET  /api/v1/cari-hareketler
# ════════════════════════════════════════════════════════════

@app.get("/api/v1/cari-hareketler", response_model=List[CariHareketRead], tags=["Cari Hareket"])
def cari_hareketler_listele(
    cari_id: Optional[int] = Query(None),
    hareket_tipi: Optional[str] = Query(None, description="BORC | ALACAK"),
    tarih_baslangic: Optional[date] = Query(None),
    tarih_bitis: Optional[date] = Query(None),
    db: Session = Depends(get_db)
):
    q = db.query(CariHareket)
    if cari_id:
        q = q.filter(CariHareket.cari_id == cari_id)
    if hareket_tipi:
        q = q.filter(CariHareket.hareket_tipi == hareket_tipi)
    if tarih_baslangic:
        q = q.filter(CariHareket.tarih >= tarih_baslangic)
    if tarih_bitis:
        q = q.filter(CariHareket.tarih <= tarih_bitis)
    return q.order_by(CariHareket.tarih.desc()).all()


@app.get("/api/v1/cari-hareketler/{id}", response_model=CariHareketRead, tags=["Cari Hareket"])
def cari_hareket_getir(id: int, db: Session = Depends(get_db)):
    obj = db.get(CariHareket, id)
    if not obj:
        raise HTTPException(404, "Hareket bulunamadı")
    return obj


@app.post("/api/v1/cari-hareketler", response_model=CariHareketRead, status_code=201, tags=["Cari Hareket"])
def cari_hareket_olustur(payload: CariHareketCreate, db: Session = Depends(get_db)):
    if not db.get(Cari, payload.cari_id):
        raise HTTPException(404, "Cari bulunamadı")
    obj = CariHareket(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj


@app.delete("/api/v1/cari-hareketler/{id}", tags=["Cari Hareket"])
def cari_hareket_sil(id: int, db: Session = Depends(get_db)):
    obj = db.get(CariHareket, id)
    if not obj:
        raise HTTPException(404, "Hareket bulunamadı")
    db.delete(obj); db.commit()
    return {"ok": True, "mesaj": "Hareket silindi"}


# ════════════════════════════════════════════════════════════
#  STOK  /api/v1/stoklar
# ════════════════════════════════════════════════════════════

@app.get("/api/v1/stoklar", response_model=List[StokKartiRead], tags=["Stok"])
def stoklar_listele(
    tip: Optional[str] = Query(None, description="MALZEME | HIZMET"),
    aktif: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    q = db.query(StokKarti)
    if tip:
        q = q.filter(StokKarti.tip == tip)
    if aktif is not None:
        q = q.filter(StokKarti.aktif == aktif)
    return q.order_by(StokKarti.ad).all()


@app.get("/api/v1/stoklar/{id}", response_model=StokKartiRead, tags=["Stok"])
def stok_getir(id: int, db: Session = Depends(get_db)):
    obj = db.get(StokKarti, id)
    if not obj:
        raise HTTPException(404, "Stok kartı bulunamadı")
    return obj


@app.get("/api/v1/stoklar/{id}/miktar", tags=["Stok"])
def stok_miktar(id: int, db: Session = Depends(get_db)):
    obj = db.get(StokKarti, id)
    if not obj:
        raise HTTPException(404, "Stok kartı bulunamadı")
    if obj.tip == "HIZMET":
        return {"stok_id": id, "tip": "HIZMET", "miktar": None}
    giris = db.query(func.sum(StokHareket.miktar)).filter(
        StokHareket.stok_id == id, StokHareket.hareket_tipi == "GIRIS").scalar() or 0
    cikis = db.query(func.sum(StokHareket.miktar)).filter(
        StokHareket.stok_id == id, StokHareket.hareket_tipi == "CIKIS").scalar() or 0
    return {"stok_id": id, "tip": "MALZEME", "miktar": float(giris) - float(cikis)}


@app.post("/api/v1/stoklar", response_model=StokKartiRead, status_code=201, tags=["Stok"])
def stok_olustur(payload: StokKartiCreate, db: Session = Depends(get_db)):
    obj = StokKarti(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj


@app.put("/api/v1/stoklar/{id}", response_model=StokKartiRead, tags=["Stok"])
def stok_guncelle(id: int, payload: StokKartiCreate, db: Session = Depends(get_db)):
    obj = db.get(StokKarti, id)
    if not obj:
        raise HTTPException(404, "Stok kartı bulunamadı")
    for k, v in payload.model_dump().items():
        setattr(obj, k, v)
    db.commit(); db.refresh(obj)
    return obj


@app.delete("/api/v1/stoklar/{id}", tags=["Stok"])
def stok_sil(id: int, db: Session = Depends(get_db)):
    obj = db.get(StokKarti, id)
    if not obj:
        raise HTTPException(404, "Stok kartı bulunamadı")
    obj.aktif = False; db.commit()
    return {"ok": True, "mesaj": "Stok kartı pasife alındı"}


# ════════════════════════════════════════════════════════════
#  STOK HAREKET  /api/v1/stok-hareketler
# ════════════════════════════════════════════════════════════

@app.get("/api/v1/stok-hareketler", response_model=List[StokHareketRead], tags=["Stok Hareket"])
def stok_hareketler_listele(
    stok_id: Optional[int] = Query(None),
    hareket_tipi: Optional[str] = Query(None, description="GIRIS | CIKIS"),
    tarih_baslangic: Optional[date] = Query(None),
    tarih_bitis: Optional[date] = Query(None),
    db: Session = Depends(get_db)
):
    q = db.query(StokHareket)
    if stok_id:
        q = q.filter(StokHareket.stok_id == stok_id)
    if hareket_tipi:
        q = q.filter(StokHareket.hareket_tipi == hareket_tipi)
    if tarih_baslangic:
        q = q.filter(StokHareket.tarih >= tarih_baslangic)
    if tarih_bitis:
        q = q.filter(StokHareket.tarih <= tarih_bitis)
    return q.order_by(StokHareket.tarih.desc()).all()


@app.get("/api/v1/stok-hareketler/{id}", response_model=StokHareketRead, tags=["Stok Hareket"])
def stok_hareket_getir(id: int, db: Session = Depends(get_db)):
    obj = db.get(StokHareket, id)
    if not obj:
        raise HTTPException(404, "Stok hareketi bulunamadı")
    return obj


@app.post("/api/v1/stok-hareketler", response_model=StokHareketRead, status_code=201, tags=["Stok Hareket"])
def stok_hareket_olustur(payload: StokHareketCreate, db: Session = Depends(get_db)):
    if not db.get(StokKarti, payload.stok_id):
        raise HTTPException(404, "Stok kartı bulunamadı")
    obj = StokHareket(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj


@app.delete("/api/v1/stok-hareketler/{id}", tags=["Stok Hareket"])
def stok_hareket_sil(id: int, db: Session = Depends(get_db)):
    obj = db.get(StokHareket, id)
    if not obj:
        raise HTTPException(404, "Stok hareketi bulunamadı")
    db.delete(obj); db.commit()
    return {"ok": True, "mesaj": "Hareket silindi"}


# ════════════════════════════════════════════════════════════
#  BELGE  /api/v1/belgeler
# ════════════════════════════════════════════════════════════

@app.get("/api/v1/belgeler", tags=["Belge"])
def belgeler_listele(
    belge_tip: Optional[str] = Query(None, description="TALEP | SIPARIS | IRSALIYE | FATURA"),
    cari_tip: Optional[str] = Query(None, description="SATIS | ALIS"),
    durum: Optional[str] = Query(None, description="ACIK | ONAYLANDI | IPTAL"),
    cari_id: Optional[int] = Query(None),
    tarih_baslangic: Optional[date] = Query(None),
    tarih_bitis: Optional[date] = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db)
):
    q = db.query(BelgeBaslik)
    if belge_tip:
        q = q.filter(BelgeBaslik.belge_tip == belge_tip.upper())
    if cari_tip:
        q = q.filter(BelgeBaslik.cari_tip == cari_tip.upper())
    if durum:
        q = q.filter(BelgeBaslik.durum == durum.upper())
    if cari_id:
        q = q.filter(BelgeBaslik.cari_id == cari_id)
    if tarih_baslangic:
        q = q.filter(BelgeBaslik.tarih >= tarih_baslangic)
    if tarih_bitis:
        q = q.filter(BelgeBaslik.tarih <= tarih_bitis)
    sonuclar = q.order_by(BelgeBaslik.tarih.desc()).limit(limit).all()
    return [BelgeBaslikRead.from_orm_obj(b) for b in sonuclar]


@app.get("/api/v1/belgeler/{id}", tags=["Belge"])
def belge_getir(id: int, db: Session = Depends(get_db)):
    obj = db.get(BelgeBaslik, id)
    if not obj:
        raise HTTPException(404, "Belge bulunamadı")
    return BelgeBaslikRead.from_orm_obj(obj)


@app.post("/api/v1/belgeler", status_code=201, tags=["Belge"])
def belge_olustur(payload: BelgeBaslikCreate, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude={"satirlar"})
    baslik = BelgeBaslik(**data)
    db.add(baslik); db.flush()
    for s_data in payload.satirlar:
        satir = BelgeSatir(baslik_id=baslik.id, **s_data.model_dump())
        db.add(satir)
    db.commit(); db.refresh(baslik)
    return BelgeBaslikRead.from_orm_obj(baslik)


@app.put("/api/v1/belgeler/{id}", tags=["Belge"])
def belge_guncelle(id: int, payload: BelgeBaslikCreate, db: Session = Depends(get_db)):
    baslik = db.get(BelgeBaslik, id)
    if not baslik:
        raise HTTPException(404, "Belge bulunamadı")
    data = payload.model_dump(exclude={"satirlar"})
    for k, v in data.items():
        setattr(baslik, k, v)
    # Satırları sıfırla ve yeniden ekle
    db.query(BelgeSatir).filter_by(baslik_id=id).delete()
    db.flush()
    for s_data in payload.satirlar:
        satir = BelgeSatir(baslik_id=id, **s_data.model_dump())
        db.add(satir)
    db.commit(); db.refresh(baslik)
    return BelgeBaslikRead.from_orm_obj(baslik)


@app.delete("/api/v1/belgeler/{id}", tags=["Belge"])
def belge_sil(id: int, db: Session = Depends(get_db)):
    obj = db.get(BelgeBaslik, id)
    if not obj:
        raise HTTPException(404, "Belge bulunamadı")
    db.query(CariHareket).filter_by(kaynak_tip="FATURA", kaynak_id=id).delete()
    db.query(StokHareket).filter(StokHareket.belge_no == obj.belge_no).delete()
    db.delete(obj); db.commit()
    return {"ok": True, "mesaj": "Belge silindi"}


# ════════════════════════════════════════════════════════════
#  BELGE SATIR  /api/v1/belge-satirlari
# ════════════════════════════════════════════════════════════

@app.get("/api/v1/belge-satirlari", response_model=List[BelgeSatirRead], tags=["Belge Satır"])
def belge_satirlari_listele(
    baslik_id: Optional[int] = Query(None),
    stok_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    q = db.query(BelgeSatir)
    if baslik_id:
        q = q.filter(BelgeSatir.baslik_id == baslik_id)
    if stok_id:
        q = q.filter(BelgeSatir.stok_id == stok_id)
    return q.order_by(BelgeSatir.baslik_id, BelgeSatir.sira_no).all()


@app.get("/api/v1/belge-satirlari/{id}", response_model=BelgeSatirRead, tags=["Belge Satır"])
def belge_satir_getir(id: int, db: Session = Depends(get_db)):
    obj = db.get(BelgeSatir, id)
    if not obj:
        raise HTTPException(404, "Satır bulunamadı")
    return obj


# ════════════════════════════════════════════════════════════
#  ÇALIŞTIRMA
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
