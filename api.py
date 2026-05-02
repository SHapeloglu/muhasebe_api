"""
Muhasebe API v2
===============
Flask muhasebe uygulamasının tüm tablolarını FastAPI ile dışarıya açar.
v2 Yenilikleri: Şirket, Depo, Kullanıcı/Yetki, Finans (Banka/Kasa/Çek-Senet/CariF işi),
                Adres Referansları, HesapGrubu, TaksitPlan, DövizTürü, Rapor

Kurulum:
    pip install fastapi uvicorn sqlalchemy pymysql cryptography pydantic werkzeug

Çalıştırma:
    uvicorn api:app --reload --port 8000
    veya: python api.py
"""

from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Any, Dict
from enum import Enum as PyEnum

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean, Numeric,
    Date, DateTime, Text, SmallInteger, ForeignKey, Enum,
    func, Index, UniqueConstraint
)
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
        pool_size=cfg.POOL_SIZE, max_overflow=cfg.MAX_OVERFLOW,
        pool_timeout=cfg.POOL_TIMEOUT, pool_recycle=cfg.POOL_RECYCLE,
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


def d(v) -> Optional[float]:
    """Decimal → float (None güvenli)."""
    return float(v) if v is not None else None


# ════════════════════════════════════════════════════════════
#  SQLALCHEMY MODELLERİ
# ════════════════════════════════════════════════════════════

class Sirket(Base):
    __tablename__ = 'sirket'
    id               = Column(Integer, primary_key=True, autoincrement=True)
    kod              = Column(String(20), unique=True, nullable=False)
    unvan            = Column(String(200), nullable=False)
    vergi_no         = Column(String(20))
    vergi_dairesi    = Column(String(100))
    telefon          = Column(String(20))
    email            = Column(String(100))
    adres            = Column(Text)
    logo_url         = Column(String(300))
    aktif            = Column(Boolean, default=True, nullable=False)
    olusturma_tarihi = Column(DateTime, default=datetime.now)


class Depo(Base):
    __tablename__ = 'depo'
    id        = Column(Integer, primary_key=True, autoincrement=True)
    sirket_id = Column(Integer, ForeignKey('sirket.id', ondelete='CASCADE'), nullable=False)
    kod       = Column(String(20), nullable=False)
    ad        = Column(String(100), nullable=False)
    adres     = Column(Text)
    aktif     = Column(Boolean, default=True, nullable=False)
    __table_args__ = (UniqueConstraint('sirket_id', 'kod', name='uq_depo_sirket_kod'),)


class NumaraSira(Base):
    __tablename__ = 'numara_sira'
    id        = Column(Integer, primary_key=True, autoincrement=True)
    sirket_id = Column(Integer, ForeignKey('sirket.id', ondelete='CASCADE'), nullable=False)
    belge_tip = Column(Enum('TALEP', 'SIPARIS', 'IRSALIYE', 'FATURA'), nullable=False)
    cari_tip  = Column(Enum('SATIS', 'ALIS'), nullable=False)
    prefix    = Column(String(10), nullable=False)
    yil       = Column(SmallInteger, nullable=False)
    son_sayi  = Column(Integer, default=0, nullable=False)
    basamak   = Column(SmallInteger, default=5)
    __table_args__ = (
        UniqueConstraint('sirket_id', 'belge_tip', 'cari_tip', 'yil', name='uq_ns_sirket_tip_yil'),
    )


class DovizTuru(Base):
    __tablename__ = 'doviz_turu'
    id     = Column(Integer, primary_key=True, autoincrement=True)
    kod    = Column(String(5), unique=True, nullable=False)
    ad     = Column(String(50), nullable=False)
    sembol = Column(String(5))
    aktif  = Column(Boolean, default=True, nullable=False)


class BankaHesap(Base):
    __tablename__ = 'banka_hesap'
    id         = Column(Integer, primary_key=True, autoincrement=True)
    sirket_id  = Column(Integer, ForeignKey('sirket.id', ondelete='CASCADE'), nullable=False)
    kod        = Column(String(20), nullable=False)
    banka_adi  = Column(String(100), nullable=False)
    sube_adi   = Column(String(100))
    sube_kodu  = Column(String(20))
    hesap_no   = Column(String(50))
    iban       = Column(String(34))
    doviz_id   = Column(Integer, ForeignKey('doviz_turu.id', ondelete='RESTRICT'))
    aciklama   = Column(String(200))
    aktif      = Column(Boolean, default=True, nullable=False)
    __table_args__ = (UniqueConstraint('sirket_id', 'kod', name='uq_banka_hesap_kod'),)


class BankaHareket(Base):
    __tablename__ = 'banka_hareket'
    id               = Column(Integer, primary_key=True, autoincrement=True)
    banka_hesap_id   = Column(Integer, ForeignKey('banka_hesap.id', ondelete='CASCADE'), nullable=False)
    tarih            = Column(Date, nullable=False, default=date.today)
    fisno            = Column(String(30))
    fis_tipi         = Column(String(20), nullable=False)
    yon              = Column(Enum('GIRIS', 'CIKIS'), nullable=False)
    tutar            = Column(Numeric(15, 2), nullable=False)
    aciklama         = Column(String(500))
    cari_id          = Column(Integer, ForeignKey('cari.id', ondelete='SET NULL'))
    karsit_hesap_id  = Column(Integer, ForeignKey('banka_hesap.id', ondelete='SET NULL'))
    karsit_kasa_id   = Column(Integer, ForeignKey('kasa_hesap.id', ondelete='SET NULL'))
    olusturma_tarihi = Column(DateTime, default=datetime.now)
    __table_args__ = (Index('ix_banka_hrkt_hesap_tarih', 'banka_hesap_id', 'tarih'),)


class KasaHesap(Base):
    __tablename__ = 'kasa_hesap'
    id        = Column(Integer, primary_key=True, autoincrement=True)
    sirket_id = Column(Integer, ForeignKey('sirket.id', ondelete='CASCADE'), nullable=False)
    kod       = Column(String(20), nullable=False)
    ad        = Column(String(100), nullable=False)
    doviz_id  = Column(Integer, ForeignKey('doviz_turu.id', ondelete='RESTRICT'))
    aciklama  = Column(String(200))
    aktif     = Column(Boolean, default=True, nullable=False)
    __table_args__ = (UniqueConstraint('sirket_id', 'kod', name='uq_kasa_hesap_kod'),)


class KasaHareket(Base):
    __tablename__ = 'kasa_hareket'
    id              = Column(Integer, primary_key=True, autoincrement=True)
    kasa_hesap_id   = Column(Integer, ForeignKey('kasa_hesap.id', ondelete='CASCADE'), nullable=False)
    tarih           = Column(Date, nullable=False, default=date.today)
    fisno           = Column(String(30))
    fis_tipi        = Column(String(20), nullable=False)
    yon             = Column(Enum('GIRIS', 'CIKIS'), nullable=False)
    tutar           = Column(Numeric(15, 2), nullable=False)
    aciklama        = Column(String(500))
    cari_id         = Column(Integer, ForeignKey('cari.id', ondelete='SET NULL'))
    karsit_kasa_id  = Column(Integer, ForeignKey('kasa_hesap.id', ondelete='SET NULL'))
    karsit_banka_id = Column(Integer, ForeignKey('banka_hesap.id', ondelete='SET NULL'))
    olusturma_tarihi= Column(DateTime, default=datetime.now)
    __table_args__ = (Index('ix_kasa_hrkt_hesap_tarih', 'kasa_hesap_id', 'tarih'),)


class CariHesapFis(Base):
    __tablename__ = 'cari_hesap_fis'
    id               = Column(Integer, primary_key=True, autoincrement=True)
    sirket_id        = Column(Integer, ForeignKey('sirket.id', ondelete='SET NULL'))
    fisno            = Column(String(30), unique=True, nullable=False)
    tarih            = Column(Date, nullable=False, default=date.today)
    aciklama         = Column(String(500))
    olusturma_tarihi = Column(DateTime, default=datetime.now)
    satirlar         = relationship('CariHesapFisSatir', backref='fis',
                                    cascade='all, delete-orphan')


class CariHesapFisSatir(Base):
    __tablename__ = 'cari_hesap_fis_satir'
    id           = Column(Integer, primary_key=True, autoincrement=True)
    fis_id       = Column(Integer, ForeignKey('cari_hesap_fis.id', ondelete='CASCADE'), nullable=False)
    cari_id      = Column(Integer, ForeignKey('cari.id', ondelete='RESTRICT'), nullable=False)
    hareket_tipi = Column(Enum('BORC', 'ALACAK'), nullable=False)
    tutar        = Column(Numeric(15, 2), nullable=False)
    aciklama     = Column(String(300))


class CariBankaHesap(Base):
    __tablename__ = 'cari_banka_hesap'
    id          = Column(Integer, primary_key=True, autoincrement=True)
    cari_id     = Column(Integer, ForeignKey('cari.id', ondelete='CASCADE'), nullable=False)
    banka_adi   = Column(String(100), nullable=False)
    sube_adi    = Column(String(100))
    hesap_no    = Column(String(50))
    iban        = Column(String(34))
    doviz_id    = Column(Integer, ForeignKey('doviz_turu.id', ondelete='SET NULL'))
    aciklama    = Column(String(200))
    varsayilan  = Column(Boolean, default=False, nullable=False)
    aktif       = Column(Boolean, default=True, nullable=False)
    __table_args__ = (Index('ix_cari_banka_cari', 'cari_id'),)


class CariIletisim(Base):
    __tablename__ = 'cari_iletisim'
    id         = Column(Integer, primary_key=True, autoincrement=True)
    cari_id    = Column(Integer, ForeignKey('cari.id', ondelete='CASCADE'), nullable=False)
    tip        = Column(Enum('TELEFON', 'CEP', 'FAX', 'EMAIL', 'WEB', 'DIGER'), nullable=False)
    deger      = Column(String(200), nullable=False)
    aciklama   = Column(String(100))
    varsayilan = Column(Boolean, default=False, nullable=False)
    aktif      = Column(Boolean, default=True, nullable=False)
    __table_args__ = (Index('ix_ci_cari', 'cari_id'),)


class Kullanici(Base):
    __tablename__ = 'kullanici'
    id               = Column(Integer, primary_key=True, autoincrement=True)
    ad_soyad         = Column(String(100), nullable=False)
    email            = Column(String(150), unique=True, nullable=False)
    sifre_hash       = Column(String(256), nullable=False)
    rol              = Column(Enum('ADMIN', 'STANDART', 'SADECE_OKUMA'), nullable=False, default='STANDART')
    tema             = Column(String(20), default='dark')
    aktif            = Column(Boolean, default=True, nullable=False)
    olusturma_tarihi = Column(DateTime, default=datetime.now)


class KullaniciSirketYetki(Base):
    __tablename__ = 'kullanici_sirket_yetki'
    id           = Column(Integer, primary_key=True, autoincrement=True)
    kullanici_id = Column(Integer, ForeignKey('kullanici.id', ondelete='CASCADE'), nullable=False)
    sirket_id    = Column(Integer, ForeignKey('sirket.id', ondelete='CASCADE'), nullable=False)
    __table_args__ = (UniqueConstraint('kullanici_id', 'sirket_id', name='uq_ksy'),)


class KullaniciDepoYetki(Base):
    __tablename__ = 'kullanici_depo_yetki'
    id           = Column(Integer, primary_key=True, autoincrement=True)
    kullanici_id = Column(Integer, ForeignKey('kullanici.id', ondelete='CASCADE'), nullable=False)
    depo_id      = Column(Integer, ForeignKey('depo.id', ondelete='CASCADE'), nullable=False)
    __table_args__ = (UniqueConstraint('kullanici_id', 'depo_id', name='uq_kdy'),)


class KullaniciBelgeYetki(Base):
    __tablename__ = 'kullanici_belge_yetki'
    id           = Column(Integer, primary_key=True, autoincrement=True)
    kullanici_id = Column(Integer, ForeignKey('kullanici.id', ondelete='CASCADE'), nullable=False)
    belge_tip    = Column(Enum('TALEP', 'SIPARIS', 'IRSALIYE', 'FATURA'), nullable=False)
    cari_tip     = Column(Enum('SATIS', 'ALIS', 'HER_IKISI'), nullable=False, default='HER_IKISI')
    yazma        = Column(Boolean, default=True)
    __table_args__ = (UniqueConstraint('kullanici_id', 'belge_tip', 'cari_tip', name='uq_kbty'),)


class CekSenet(Base):
    __tablename__ = 'cek_senet'
    id               = Column(Integer, primary_key=True, autoincrement=True)
    sirket_id        = Column(Integer, ForeignKey('sirket.id', ondelete='CASCADE'), nullable=False)
    tip              = Column(Enum('CEK', 'SENET'), nullable=False)
    yon              = Column(Enum('ALACAK', 'BORC'), nullable=False)
    seri_no          = Column(String(50))
    banka            = Column(String(100))
    sube             = Column(String(100))
    kesideci         = Column(String(200))
    cari_id          = Column(Integer, ForeignKey('cari.id', ondelete='SET NULL'))
    tutar            = Column(Numeric(15, 2), nullable=False)
    doviz_id         = Column(Integer, ForeignKey('doviz_turu.id', ondelete='SET NULL'))
    vade_tarihi      = Column(Date, nullable=False)
    durum            = Column(Enum('PORTFOY', 'TAHSILDE', 'TAHSIL_EDILDI', 'CIRO_EDILDI', 'PROTESTO', 'IPTAL'),
                              nullable=False, default='PORTFOY')
    aciklama         = Column(String(300))
    olusturma_tarihi = Column(DateTime, default=datetime.now)
    __table_args__ = (
        Index('ix_ceksenet_sirket', 'sirket_id'),
        Index('ix_ceksenet_vade', 'vade_tarihi'),
    )


class TaksitPlan(Base):
    __tablename__ = 'taksit_plan'
    id           = Column(Integer, primary_key=True, autoincrement=True)
    belge_id     = Column(Integer, ForeignKey('belge_baslik.id', ondelete='CASCADE'), nullable=False)
    taksit_no    = Column(SmallInteger, nullable=False)
    vade_tarihi  = Column(Date, nullable=False)
    tutar        = Column(Numeric(15, 2), nullable=False)
    odendi       = Column(Boolean, default=False)
    odeme_tarihi = Column(Date)
    aciklama     = Column(String(200))
    __table_args__ = (Index('ix_taksit_belge', 'belge_id'),)


class HesapGrubu(Base):
    __tablename__ = 'hesap_grubu'
    id        = Column(Integer, primary_key=True, autoincrement=True)
    tip       = Column(Enum('CARI', 'STOK'), nullable=False)
    seviye    = Column(SmallInteger, nullable=False, default=1)
    parent_id = Column(Integer, ForeignKey('hesap_grubu.id', ondelete='RESTRICT'))
    kod       = Column(String(20), nullable=False)
    ad        = Column(String(100), nullable=False)
    aciklama  = Column(String(200))
    aktif     = Column(Boolean, default=True, nullable=False)
    __table_args__ = (
        UniqueConstraint('tip', 'kod', name='uq_hesapgrubu_tip_kod'),
        Index('ix_hg_tip_seviye', 'tip', 'seviye'),
        Index('ix_hg_parent', 'parent_id'),
    )


class Rapor(Base):
    __tablename__ = 'rapor'
    id               = Column(Integer, primary_key=True, autoincrement=True)
    ad               = Column(String(100), nullable=False)
    aciklama         = Column(Text)
    sql_sorgu        = Column(Text, nullable=False)
    kategori         = Column(String(50))
    olusturma_tarihi = Column(DateTime, default=datetime.now)
    aktif            = Column(Boolean, default=True, nullable=False)


class RaporFiltre(Base):
    __tablename__ = 'rapor_filtre'
    id           = Column(Integer, primary_key=True, autoincrement=True)
    rapor_id     = Column(Integer, ForeignKey('rapor.id', ondelete='CASCADE'), nullable=False)
    sira         = Column(SmallInteger, default=1)
    etiket       = Column(String(50), nullable=False)
    parametre    = Column(String(30), nullable=False)
    tip          = Column(Enum('TARIH', 'METIN', 'SAYI', 'SECIM'), nullable=False, default='METIN')
    secim_deger  = Column(String(500))
    varsayilan   = Column(String(100))


class Ulke(Base):
    __tablename__ = 'ulke'
    id    = Column(Integer, primary_key=True, autoincrement=True)
    kod   = Column(String(3), unique=True, nullable=False)
    ad    = Column(String(100), nullable=False)
    aktif = Column(Boolean, default=True, nullable=False)


class Il(Base):
    __tablename__ = 'il'
    id      = Column(Integer, primary_key=True, autoincrement=True)
    ulke_id = Column(Integer, ForeignKey('ulke.id', ondelete='CASCADE'), nullable=False)
    plaka   = Column(String(5))
    ad      = Column(String(100), nullable=False)
    aktif   = Column(Boolean, default=True, nullable=False)
    __table_args__ = (Index('ix_il_ulke', 'ulke_id'),)


class Ilce(Base):
    __tablename__ = 'ilce'
    id    = Column(Integer, primary_key=True, autoincrement=True)
    il_id = Column(Integer, ForeignKey('il.id', ondelete='CASCADE'), nullable=False)
    ad    = Column(String(100), nullable=False)
    aktif = Column(Boolean, default=True, nullable=False)
    __table_args__ = (Index('ix_ilce_il', 'il_id'),)


class Mahalle(Base):
    __tablename__ = 'mahalle'
    id         = Column(Integer, primary_key=True, autoincrement=True)
    ilce_id    = Column(Integer, ForeignKey('ilce.id', ondelete='CASCADE'), nullable=False)
    ad         = Column(String(100), nullable=False)
    posta_kodu = Column(String(10))
    aktif      = Column(Boolean, default=True, nullable=False)
    __table_args__ = (Index('ix_mahalle_ilce', 'ilce_id'),)


class CariAdres(Base):
    __tablename__ = 'cari_adres'
    id          = Column(Integer, primary_key=True, autoincrement=True)
    cari_id     = Column(Integer, ForeignKey('cari.id', ondelete='CASCADE'), nullable=False)
    adres_tipi  = Column(Enum('MERKEZ', 'SUBE', 'FATURA', 'SEVKIYAT', 'DIGER'), nullable=False, default='MERKEZ')
    ulke_id     = Column(Integer, ForeignKey('ulke.id', ondelete='SET NULL'))
    il_id       = Column(Integer, ForeignKey('il.id', ondelete='SET NULL'))
    ilce_id     = Column(Integer, ForeignKey('ilce.id', ondelete='SET NULL'))
    mahalle_id  = Column(Integer, ForeignKey('mahalle.id', ondelete='SET NULL'))
    sokak       = Column(String(200))
    bina_no     = Column(String(20))
    daire_no    = Column(String(20))
    posta_kodu  = Column(String(10))
    aciklama    = Column(String(300))
    varsayilan  = Column(Boolean, default=False, nullable=False)
    aktif       = Column(Boolean, default=True, nullable=False)
    __table_args__ = (Index('ix_cari_adres_cari', 'cari_id'),)


class BirimGrubu(Base):
    __tablename__ = 'birim_grubu'
    id       = Column(Integer, primary_key=True, autoincrement=True)
    ad       = Column(String(50), unique=True, nullable=False)
    aciklama = Column(String(200))
    aktif    = Column(Boolean, default=True, nullable=False)
    birimler = relationship('Birim', backref='grup', lazy='dynamic', foreign_keys='Birim.grup_id')


class Birim(Base):
    __tablename__ = 'birim'
    id       = Column(Integer, primary_key=True, autoincrement=True)
    grup_id  = Column(Integer, ForeignKey('birim_grubu.id', ondelete='RESTRICT'), nullable=False)
    kod      = Column(String(20), unique=True, nullable=False)
    ad       = Column(String(50), nullable=False)
    katsayi  = Column(Numeric(20, 10), nullable=False, default=1.0)
    taban_mi = Column(Boolean, default=False, nullable=False)
    aktif    = Column(Boolean, default=True, nullable=False)
    __table_args__ = (Index('ix_birim_grup', 'grup_id'),)


class BirimDonusum(Base):
    __tablename__ = 'birim_donusum'
    id              = Column(Integer, primary_key=True, autoincrement=True)
    kaynak_birim_id = Column(Integer, ForeignKey('birim.id', ondelete='CASCADE'), nullable=False)
    hedef_birim_id  = Column(Integer, ForeignKey('birim.id', ondelete='CASCADE'), nullable=False)
    carpan          = Column(Numeric(20, 10), nullable=False)
    aciklama        = Column(String(200))
    aktif           = Column(Boolean, default=True, nullable=False)
    __table_args__ = (
        UniqueConstraint('kaynak_birim_id', 'hedef_birim_id', name='uq_donusum_kh'),
        Index('ix_donusum_kaynak', 'kaynak_birim_id'),
    )


class Cari(Base):
    __tablename__ = 'cari'
    id               = Column(Integer, primary_key=True, autoincrement=True)
    kod              = Column(String(20), unique=True, nullable=False)
    unvan            = Column(String(200), nullable=False)
    tip              = Column(Enum('ALICI', 'SATICI', 'HER_IKISI'), nullable=False)
    vergi_no         = Column(String(20))
    vergi_dairesi    = Column(String(100))
    telefon          = Column(String(20))
    email            = Column(String(100))
    adres            = Column(Text)
    sehir            = Column(String(50))
    hesap_grubu_id   = Column(Integer, ForeignKey('hesap_grubu.id', ondelete='SET NULL'))
    aktif            = Column(Boolean, default=True, nullable=False)
    olusturma_tarihi = Column(DateTime, default=datetime.now)


class CariHareket(Base):
    __tablename__ = 'cari_hareket'
    id           = Column(Integer, primary_key=True, autoincrement=True)
    cari_id      = Column(Integer, ForeignKey('cari.id', ondelete='CASCADE'), nullable=False)
    tarih        = Column(Date, nullable=False, default=date.today)
    belge_no     = Column(String(50))
    aciklama     = Column(String(500))
    hareket_tipi = Column(Enum('BORC', 'ALACAK'), nullable=False)
    tutar        = Column(Numeric(15, 2), nullable=False)
    kaynak_tip   = Column(String(20))
    kaynak_id    = Column(Integer)
    __table_args__ = (Index('ix_ch_cari_tarih', 'cari_id', 'tarih'),)


class StokKarti(Base):
    __tablename__ = 'stok_karti'
    id               = Column(Integer, primary_key=True, autoincrement=True)
    kod              = Column(String(50), unique=True, nullable=False)
    ad               = Column(String(200), nullable=False)
    tip              = Column(Enum('MALZEME', 'HIZMET'), nullable=False)
    birim_id         = Column(Integer, ForeignKey('birim.id', ondelete='RESTRICT'), nullable=False)
    kdv_orani        = Column(Numeric(5, 2), default=20.00)
    satis_fiyati     = Column(Numeric(15, 4), default=0.0)
    alis_fiyati      = Column(Numeric(15, 4), default=0.0)
    aciklama         = Column(Text)
    aktif            = Column(Boolean, default=True, nullable=False)
    hesap_grubu_id   = Column(Integer, ForeignKey('hesap_grubu.id', ondelete='SET NULL'))
    olusturma_tarihi = Column(DateTime, default=datetime.now)


class StokHareket(Base):
    __tablename__ = 'stok_hareket'
    id              = Column(Integer, primary_key=True, autoincrement=True)
    stok_id         = Column(Integer, ForeignKey('stok_karti.id', ondelete='CASCADE'), nullable=False)
    tarih           = Column(Date, nullable=False, default=date.today)
    belge_no        = Column(String(50))
    hareket_tipi    = Column(Enum('GIRIS', 'CIKIS'), nullable=False)
    birim_id        = Column(Integer, ForeignKey('birim.id', ondelete='RESTRICT'))
    miktar          = Column(Numeric(15, 4), nullable=False)
    cevrilen_miktar = Column(Numeric(15, 4))
    birim_fiyat     = Column(Numeric(15, 4))
    aciklama        = Column(String(500))
    __table_args__ = (Index('ix_sh_stok_tarih', 'stok_id', 'tarih'),)


class BelgeBaslik(Base):
    __tablename__ = 'belge_baslik'
    id               = Column(Integer, primary_key=True, autoincrement=True)
    belge_tip        = Column(Enum('TALEP', 'SIPARIS', 'IRSALIYE', 'FATURA'), nullable=False)
    belge_no         = Column(String(50), unique=True, nullable=False)
    tarih            = Column(Date, nullable=False, default=date.today)
    vade_tarihi      = Column(Date)
    cari_id          = Column(Integer, ForeignKey('cari.id', ondelete='SET NULL'))
    cari_tip         = Column(Enum('SATIS', 'ALIS'), nullable=False, default='SATIS')
    aciklama         = Column(Text)
    durum            = Column(Enum('ACIK', 'ONAYLANDI', 'IPTAL'), default='ACIK')
    kaynak_belge_id  = Column(Integer, ForeignKey('belge_baslik.id', ondelete='SET NULL'))
    toplam_kdvsiz    = Column(Numeric(15, 2), default=0.00)
    toplam_kdv       = Column(Numeric(15, 2), default=0.00)
    toplam_kdvli     = Column(Numeric(15, 2), default=0.00)
    sirket_id        = Column(Integer, ForeignKey('sirket.id', ondelete='SET NULL'))
    depo_id          = Column(Integer, ForeignKey('depo.id', ondelete='SET NULL'))
    evrak_no         = Column(String(50))
    olusturma_tarihi = Column(DateTime, default=datetime.now)
    satirlar         = relationship('BelgeSatir', backref='baslik',
                                    cascade='all, delete-orphan', order_by='BelgeSatir.sira_no')
    __table_args__ = (
        Index('ix_bb_tip_ctip_tarih', 'belge_tip', 'cari_tip', 'tarih'),
        Index('ix_bb_cari', 'cari_id'),
    )


class BelgeSatir(Base):
    __tablename__ = 'belge_satir'
    id           = Column(Integer, primary_key=True, autoincrement=True)
    baslik_id    = Column(Integer, ForeignKey('belge_baslik.id', ondelete='CASCADE'), nullable=False)
    sira_no      = Column(SmallInteger, nullable=False)
    stok_id      = Column(Integer, ForeignKey('stok_karti.id', ondelete='SET NULL'))
    aciklama     = Column(String(500))
    miktar       = Column(Numeric(15, 4), nullable=False, default=1.0)
    birim_id     = Column(Integer, ForeignKey('birim.id', ondelete='RESTRICT'))
    birim_fiyat  = Column(Numeric(15, 4), nullable=False, default=0.0)
    iskonto_oran = Column(Numeric(5, 2), default=0.00)
    kdv_orani    = Column(Numeric(5, 2), default=20.00)
    kdvsiz_tutar = Column(Numeric(15, 2), default=0.00)
    kdv_tutar    = Column(Numeric(15, 2), default=0.00)
    kdvli_tutar  = Column(Numeric(15, 2), default=0.00)
    __table_args__ = (Index('ix_bs_baslik', 'baslik_id'),)


# ════════════════════════════════════════════════════════════
#  PYDANTIC ŞEMALARI
# ════════════════════════════════════════════════════════════

# ── Şirket ──────────────────────────────────────────────────
class SirketCreate(BaseModel):
    kod: str
    unvan: str
    vergi_no: Optional[str] = None
    vergi_dairesi: Optional[str] = None
    telefon: Optional[str] = None
    email: Optional[str] = None
    adres: Optional[str] = None
    logo_url: Optional[str] = None
    aktif: bool = True

class SirketRead(SirketCreate):
    id: int
    olusturma_tarihi: Optional[datetime] = None
    class Config:
        from_attributes = True


# ── Depo ────────────────────────────────────────────────────
class DepoCreate(BaseModel):
    sirket_id: int
    kod: str
    ad: str
    adres: Optional[str] = None
    aktif: bool = True

class DepoRead(DepoCreate):
    id: int
    class Config:
        from_attributes = True


# ── NumaraSira ──────────────────────────────────────────────
class NumaraSiraCreate(BaseModel):
    sirket_id: int
    belge_tip: str
    cari_tip: str
    prefix: str
    yil: int
    son_sayi: int = 0
    basamak: int = 5

class NumaraSiraRead(NumaraSiraCreate):
    id: int
    class Config:
        from_attributes = True


# ── DövizTürü ───────────────────────────────────────────────
class DovizTuruCreate(BaseModel):
    kod: str
    ad: str
    sembol: Optional[str] = None
    aktif: bool = True

class DovizTuruRead(DovizTuruCreate):
    id: int
    class Config:
        from_attributes = True


# ── BankaHesap ──────────────────────────────────────────────
class BankaHesapCreate(BaseModel):
    sirket_id: int
    kod: str
    banka_adi: str
    sube_adi: Optional[str] = None
    sube_kodu: Optional[str] = None
    hesap_no: Optional[str] = None
    iban: Optional[str] = None
    doviz_id: Optional[int] = None
    aciklama: Optional[str] = None
    aktif: bool = True

class BankaHesapRead(BankaHesapCreate):
    id: int
    class Config:
        from_attributes = True


# ── BankaHareket ────────────────────────────────────────────
class BankaHareketCreate(BaseModel):
    banka_hesap_id: int
    tarih: date
    fisno: Optional[str] = None
    fis_tipi: str
    yon: str
    tutar: float
    aciklama: Optional[str] = None
    cari_id: Optional[int] = None
    karsit_hesap_id: Optional[int] = None
    karsit_kasa_id: Optional[int] = None

class BankaHareketRead(BankaHareketCreate):
    id: int
    olusturma_tarihi: Optional[datetime] = None
    class Config:
        from_attributes = True


# ── KasaHesap ───────────────────────────────────────────────
class KasaHesapCreate(BaseModel):
    sirket_id: int
    kod: str
    ad: str
    doviz_id: Optional[int] = None
    aciklama: Optional[str] = None
    aktif: bool = True

class KasaHesapRead(KasaHesapCreate):
    id: int
    class Config:
        from_attributes = True


# ── KasaHareket ─────────────────────────────────────────────
class KasaHareketCreate(BaseModel):
    kasa_hesap_id: int
    tarih: date
    fisno: Optional[str] = None
    fis_tipi: str
    yon: str
    tutar: float
    aciklama: Optional[str] = None
    cari_id: Optional[int] = None
    karsit_kasa_id: Optional[int] = None
    karsit_banka_id: Optional[int] = None

class KasaHareketRead(KasaHareketCreate):
    id: int
    olusturma_tarihi: Optional[datetime] = None
    class Config:
        from_attributes = True


# ── CariHesapFisSatir ───────────────────────────────────────
class CariHesapFisSatirCreate(BaseModel):
    cari_id: int
    hareket_tipi: str
    tutar: float
    aciklama: Optional[str] = None

class CariHesapFisSatirRead(CariHesapFisSatirCreate):
    id: int
    fis_id: int
    class Config:
        from_attributes = True


# ── CariHesapFis ────────────────────────────────────────────
class CariHesapFisCreate(BaseModel):
    sirket_id: Optional[int] = None
    fisno: str
    tarih: date
    aciklama: Optional[str] = None
    satirlar: List[CariHesapFisSatirCreate] = []

class CariHesapFisRead(BaseModel):
    id: int
    sirket_id: Optional[int] = None
    fisno: str
    tarih: date
    aciklama: Optional[str] = None
    olusturma_tarihi: Optional[datetime] = None
    satirlar: List[CariHesapFisSatirRead] = []
    class Config:
        from_attributes = True


# ── CariBankaHesap ──────────────────────────────────────────
class CariBankaHesapCreate(BaseModel):
    cari_id: int
    banka_adi: str
    sube_adi: Optional[str] = None
    hesap_no: Optional[str] = None
    iban: Optional[str] = None
    doviz_id: Optional[int] = None
    aciklama: Optional[str] = None
    varsayilan: bool = False
    aktif: bool = True

class CariBankaHesapRead(CariBankaHesapCreate):
    id: int
    class Config:
        from_attributes = True


# ── CariIletisim ────────────────────────────────────────────
class CariIletisimCreate(BaseModel):
    cari_id: int
    tip: str
    deger: str
    aciklama: Optional[str] = None
    varsayilan: bool = False
    aktif: bool = True

class CariIletisimRead(CariIletisimCreate):
    id: int
    class Config:
        from_attributes = True


# ── Kullanıcı ────────────────────────────────────────────────
class KullaniciCreate(BaseModel):
    ad_soyad: str
    email: str
    rol: str = 'STANDART'
    tema: str = 'dark'
    aktif: bool = True

class KullaniciRead(KullaniciCreate):
    id: int
    olusturma_tarihi: Optional[datetime] = None
    class Config:
        from_attributes = True


# ── CekSenet ────────────────────────────────────────────────
class CekSenetCreate(BaseModel):
    sirket_id: int
    tip: str
    yon: str
    seri_no: Optional[str] = None
    banka: Optional[str] = None
    sube: Optional[str] = None
    kesideci: Optional[str] = None
    cari_id: Optional[int] = None
    tutar: float
    doviz_id: Optional[int] = None
    vade_tarihi: date
    durum: str = 'PORTFOY'
    aciklama: Optional[str] = None

class CekSenetRead(CekSenetCreate):
    id: int
    olusturma_tarihi: Optional[datetime] = None
    class Config:
        from_attributes = True


# ── TaksitPlan ──────────────────────────────────────────────
class TaksitPlanCreate(BaseModel):
    belge_id: int
    taksit_no: int
    vade_tarihi: date
    tutar: float
    odendi: bool = False
    odeme_tarihi: Optional[date] = None
    aciklama: Optional[str] = None

class TaksitPlanRead(TaksitPlanCreate):
    id: int
    class Config:
        from_attributes = True


# ── HesapGrubu ──────────────────────────────────────────────
class HesapGrubuCreate(BaseModel):
    tip: str
    seviye: int = 1
    parent_id: Optional[int] = None
    kod: str
    ad: str
    aciklama: Optional[str] = None
    aktif: bool = True

class HesapGrubuRead(HesapGrubuCreate):
    id: int
    class Config:
        from_attributes = True


# ── Rapor ────────────────────────────────────────────────────
class RaporCreate(BaseModel):
    ad: str
    aciklama: Optional[str] = None
    sql_sorgu: str
    kategori: Optional[str] = None
    aktif: bool = True

class RaporRead(RaporCreate):
    id: int
    olusturma_tarihi: Optional[datetime] = None
    class Config:
        from_attributes = True


# ── Adres Referansları ──────────────────────────────────────
class UlkeRead(BaseModel):
    id: int; kod: str; ad: str; aktif: bool
    class Config:
        from_attributes = True

class IlRead(BaseModel):
    id: int; ulke_id: int; plaka: Optional[str]; ad: str; aktif: bool
    class Config:
        from_attributes = True

class IlceRead(BaseModel):
    id: int; il_id: int; ad: str; aktif: bool
    class Config:
        from_attributes = True

class MahalleRead(BaseModel):
    id: int; ilce_id: int; ad: str; posta_kodu: Optional[str]; aktif: bool
    class Config:
        from_attributes = True


# ── CariAdres ───────────────────────────────────────────────
class CariAdresCreate(BaseModel):
    cari_id: int
    adres_tipi: str = 'MERKEZ'
    ulke_id: Optional[int] = None
    il_id: Optional[int] = None
    ilce_id: Optional[int] = None
    mahalle_id: Optional[int] = None
    sokak: Optional[str] = None
    bina_no: Optional[str] = None
    daire_no: Optional[str] = None
    posta_kodu: Optional[str] = None
    aciklama: Optional[str] = None
    varsayilan: bool = False
    aktif: bool = True

class CariAdresRead(CariAdresCreate):
    id: int
    class Config:
        from_attributes = True


# ── v1 şemaları (değişmedi) ──────────────────────────────────
class BirimGrubuCreate(BaseModel):
    ad: str; aciklama: Optional[str] = None; aktif: bool = True

class BirimGrubuRead(BirimGrubuCreate):
    id: int
    class Config:
        from_attributes = True

class BirimCreate(BaseModel):
    grup_id: int; kod: str; ad: str; katsayi: float = 1.0; taban_mi: bool = False; aktif: bool = True

class BirimRead(BirimCreate):
    id: int
    class Config:
        from_attributes = True

class BirimDonusumCreate(BaseModel):
    kaynak_birim_id: int; hedef_birim_id: int; carpan: float
    aciklama: Optional[str] = None; aktif: bool = True

class BirimDonusumRead(BirimDonusumCreate):
    id: int
    class Config:
        from_attributes = True

class CariCreate(BaseModel):
    kod: str; unvan: str; tip: str
    vergi_no: Optional[str] = None; vergi_dairesi: Optional[str] = None
    telefon: Optional[str] = None; email: Optional[str] = None
    adres: Optional[str] = None; sehir: Optional[str] = None
    hesap_grubu_id: Optional[int] = None; aktif: bool = True

class CariRead(CariCreate):
    id: int; olusturma_tarihi: Optional[datetime] = None
    class Config:
        from_attributes = True

class CariHareketCreate(BaseModel):
    cari_id: int; tarih: date; belge_no: Optional[str] = None
    aciklama: Optional[str] = None; hareket_tipi: str; tutar: float
    kaynak_tip: Optional[str] = None; kaynak_id: Optional[int] = None

class CariHareketRead(CariHareketCreate):
    id: int
    class Config:
        from_attributes = True

class StokKartiCreate(BaseModel):
    kod: str; ad: str; tip: str; birim_id: int
    kdv_orani: float = 20.0; satis_fiyati: float = 0.0; alis_fiyati: float = 0.0
    aciklama: Optional[str] = None; aktif: bool = True; hesap_grubu_id: Optional[int] = None

class StokKartiRead(StokKartiCreate):
    id: int; olusturma_tarihi: Optional[datetime] = None
    class Config:
        from_attributes = True

class StokHareketCreate(BaseModel):
    stok_id: int; tarih: date; belge_no: Optional[str] = None
    hareket_tipi: str; birim_id: Optional[int] = None; miktar: float
    cevrilen_miktar: Optional[float] = None; birim_fiyat: Optional[float] = None
    aciklama: Optional[str] = None

class StokHareketRead(StokHareketCreate):
    id: int
    class Config:
        from_attributes = True

class BelgeSatirCreate(BaseModel):
    sira_no: int; stok_id: Optional[int] = None; aciklama: Optional[str] = None
    miktar: float = 1.0; birim_id: Optional[int] = None; birim_fiyat: float = 0.0
    iskonto_oran: float = 0.0; kdv_orani: float = 20.0
    kdvsiz_tutar: float = 0.0; kdv_tutar: float = 0.0; kdvli_tutar: float = 0.0

class BelgeSatirRead(BelgeSatirCreate):
    id: int; baslik_id: int
    class Config:
        from_attributes = True

class BelgeBaslikCreate(BaseModel):
    belge_tip: str; belge_no: str; tarih: date; vade_tarihi: Optional[date] = None
    cari_id: Optional[int] = None; cari_tip: str = 'SATIS'
    aciklama: Optional[str] = None; durum: str = 'ACIK'
    kaynak_belge_id: Optional[int] = None
    toplam_kdvsiz: float = 0.0; toplam_kdv: float = 0.0; toplam_kdvli: float = 0.0
    sirket_id: Optional[int] = None; depo_id: Optional[int] = None
    evrak_no: Optional[str] = None
    satirlar: List[BelgeSatirCreate] = []

class BelgeBaslikRead(BaseModel):
    id: int; belge_tip: str; belge_no: str; tarih: date; vade_tarihi: Optional[date] = None
    cari_id: Optional[int] = None; cari_tip: str; aciklama: Optional[str] = None
    durum: str; kaynak_belge_id: Optional[int] = None
    toplam_kdvsiz: Optional[float] = None; toplam_kdv: Optional[float] = None; toplam_kdvli: Optional[float] = None
    sirket_id: Optional[int] = None; depo_id: Optional[int] = None
    evrak_no: Optional[str] = None; olusturma_tarihi: Optional[datetime] = None
    satirlar: List[BelgeSatirRead] = []

    @classmethod
    def from_orm_obj(cls, obj: BelgeBaslik) -> "BelgeBaslikRead":
        return cls(
            id=obj.id, belge_tip=obj.belge_tip, belge_no=obj.belge_no,
            tarih=obj.tarih, vade_tarihi=obj.vade_tarihi,
            cari_id=obj.cari_id, cari_tip=obj.cari_tip,
            aciklama=obj.aciklama, durum=obj.durum,
            kaynak_belge_id=obj.kaynak_belge_id,
            toplam_kdvsiz=d(obj.toplam_kdvsiz), toplam_kdv=d(obj.toplam_kdv),
            toplam_kdvli=d(obj.toplam_kdvli),
            sirket_id=obj.sirket_id, depo_id=obj.depo_id,
            evrak_no=obj.evrak_no, olusturma_tarihi=obj.olusturma_tarihi,
            satirlar=[BelgeSatirRead.model_validate(s) for s in obj.satirlar],
        )


# ════════════════════════════════════════════════════════════
#  FASTAPI UYGULAMASI
# ════════════════════════════════════════════════════════════

app = FastAPI(
    title="Muhasebe API v2",
    description="Muhasebe programının tüm tablolarına REST erişimi (v2 - Finans, Şirket, Adres, Kullanıcı modülleri dahil)",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Üretimde kısıtlayın!
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Yardımcı CRUD fabrikası ────────────────────────────────

def get_or_404(db: Session, model, id: int):
    obj = db.get(model, id)
    if not obj:
        raise HTTPException(404, f"{model.__tablename__} bulunamadı (id={id})")
    return obj


# ════════════════════════════════════════════════════════════
#  GENEL
# ════════════════════════════════════════════════════════════

@app.get("/health", tags=["Genel"])
def health(db: Session = Depends(get_db)):
    from sqlalchemy import text
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "version": "2.0.0", "time": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@app.get("/api/v2/ozet", tags=["Genel"])
def ozet(sirket_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    q = db.query(BelgeBaslik)
    if sirket_id:
        q = q.filter(BelgeBaslik.sirket_id == sirket_id)

    def banka_toplam(hesap_id, yon):
        return float(db.query(func.sum(BankaHareket.tutar)).filter(
            BankaHareket.banka_hesap_id == hesap_id,
            BankaHareket.yon == yon).scalar() or 0)

    banka_toplam_giris = float(db.query(func.sum(BankaHareket.tutar)).filter_by(yon='GIRIS').scalar() or 0)
    banka_toplam_cikis = float(db.query(func.sum(BankaHareket.tutar)).filter_by(yon='CIKIS').scalar() or 0)
    kasa_toplam_giris  = float(db.query(func.sum(KasaHareket.tutar)).filter_by(yon='GIRIS').scalar() or 0)
    kasa_toplam_cikis  = float(db.query(func.sum(KasaHareket.tutar)).filter_by(yon='CIKIS').scalar() or 0)

    return {
        "cari_sayisi":       db.query(func.count(Cari.id)).filter_by(aktif=True).scalar(),
        "stok_sayisi":       db.query(func.count(StokKarti.id)).filter_by(aktif=True).scalar(),
        "birim_sayisi":      db.query(func.count(Birim.id)).filter_by(aktif=True).scalar(),
        "sirket_sayisi":     db.query(func.count(Sirket.id)).filter_by(aktif=True).scalar(),
        "acik_fatura":       q.filter_by(belge_tip='FATURA', durum='ACIK').count(),
        "acik_siparis":      q.filter_by(belge_tip='SIPARIS', durum='ACIK').count(),
        "banka_net_bakiye":  round(banka_toplam_giris - banka_toplam_cikis, 2),
        "kasa_net_bakiye":   round(kasa_toplam_giris - kasa_toplam_cikis, 2),
        "vadesi_gelen_cek":  db.query(func.count(CekSenet.id)).filter(
            CekSenet.durum == 'PORTFOY',
            CekSenet.vade_tarihi <= date.today()).scalar(),
    }


# ════════════════════════════════════════════════════════════
#  ŞİRKET  /api/v2/sirketler
# ════════════════════════════════════════════════════════════

@app.get("/api/v2/sirketler", response_model=List[SirketRead], tags=["Şirket"])
def sirketler_listele(aktif: Optional[bool] = Query(None), db: Session = Depends(get_db)):
    q = db.query(Sirket)
    if aktif is not None:
        q = q.filter(Sirket.aktif == aktif)
    return q.order_by(Sirket.unvan).all()

@app.get("/api/v2/sirketler/{id}", response_model=SirketRead, tags=["Şirket"])
def sirket_getir(id: int, db: Session = Depends(get_db)):
    return get_or_404(db, Sirket, id)

@app.post("/api/v2/sirketler", response_model=SirketRead, status_code=201, tags=["Şirket"])
def sirket_olustur(payload: SirketCreate, db: Session = Depends(get_db)):
    obj = Sirket(**payload.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj

@app.put("/api/v2/sirketler/{id}", response_model=SirketRead, tags=["Şirket"])
def sirket_guncelle(id: int, payload: SirketCreate, db: Session = Depends(get_db)):
    obj = get_or_404(db, Sirket, id)
    for k, v in payload.model_dump().items(): setattr(obj, k, v)
    db.commit(); db.refresh(obj); return obj

@app.delete("/api/v2/sirketler/{id}", tags=["Şirket"])
def sirket_sil(id: int, db: Session = Depends(get_db)):
    obj = get_or_404(db, Sirket, id); obj.aktif = False; db.commit()
    return {"ok": True, "mesaj": "Şirket pasife alındı"}


# ════════════════════════════════════════════════════════════
#  DEPO  /api/v2/depolar
# ════════════════════════════════════════════════════════════

@app.get("/api/v2/depolar", response_model=List[DepoRead], tags=["Depo"])
def depolar_listele(sirket_id: Optional[int] = Query(None), aktif: Optional[bool] = Query(None), db: Session = Depends(get_db)):
    q = db.query(Depo)
    if sirket_id: q = q.filter_by(sirket_id=sirket_id)
    if aktif is not None: q = q.filter(Depo.aktif == aktif)
    return q.order_by(Depo.ad).all()

@app.get("/api/v2/depolar/{id}", response_model=DepoRead, tags=["Depo"])
def depo_getir(id: int, db: Session = Depends(get_db)):
    return get_or_404(db, Depo, id)

@app.post("/api/v2/depolar", response_model=DepoRead, status_code=201, tags=["Depo"])
def depo_olustur(payload: DepoCreate, db: Session = Depends(get_db)):
    obj = Depo(**payload.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj

@app.put("/api/v2/depolar/{id}", response_model=DepoRead, tags=["Depo"])
def depo_guncelle(id: int, payload: DepoCreate, db: Session = Depends(get_db)):
    obj = get_or_404(db, Depo, id)
    for k, v in payload.model_dump().items(): setattr(obj, k, v)
    db.commit(); db.refresh(obj); return obj

@app.delete("/api/v2/depolar/{id}", tags=["Depo"])
def depo_sil(id: int, db: Session = Depends(get_db)):
    obj = get_or_404(db, Depo, id); obj.aktif = False; db.commit()
    return {"ok": True, "mesaj": "Depo pasife alındı"}


# ════════════════════════════════════════════════════════════
#  NUMARA SIRA  /api/v2/numara-siralar
# ════════════════════════════════════════════════════════════

@app.get("/api/v2/numara-siralar", response_model=List[NumaraSiraRead], tags=["Numara Sıra"])
def numara_siralar_listele(sirket_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    q = db.query(NumaraSira)
    if sirket_id: q = q.filter_by(sirket_id=sirket_id)
    return q.all()

@app.post("/api/v2/numara-siralar", response_model=NumaraSiraRead, status_code=201, tags=["Numara Sıra"])
def numara_sira_olustur(payload: NumaraSiraCreate, db: Session = Depends(get_db)):
    obj = NumaraSira(**payload.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj

@app.get("/api/v2/numara-siralar/sonraki", tags=["Numara Sıra"])
def sonraki_belge_no(sirket_id: int, belge_tip: str, cari_tip: str = 'SATIS', db: Session = Depends(get_db)):
    sira = db.query(NumaraSira).filter_by(
        sirket_id=sirket_id, belge_tip=belge_tip.upper(),
        cari_tip=cari_tip.upper(), yil=datetime.now().year).first()
    if not sira:
        raise HTTPException(404, "Bu kriterlere uygun numara serisi bulunamadı")
    sira.son_sayi += 1
    no = f"{sira.prefix}{str(sira.yil)[2:]}{str(sira.son_sayi).zfill(sira.basamak)}"
    db.commit()
    return {"belge_no": no, "son_sayi": sira.son_sayi}


# ════════════════════════════════════════════════════════════
#  DÖVİZ TÜRÜ  /api/v2/dovizler
# ════════════════════════════════════════════════════════════

@app.get("/api/v2/dovizler", response_model=List[DovizTuruRead], tags=["Döviz"])
def dovizler_listele(aktif: Optional[bool] = Query(None), db: Session = Depends(get_db)):
    q = db.query(DovizTuru)
    if aktif is not None: q = q.filter(DovizTuru.aktif == aktif)
    return q.order_by(DovizTuru.kod).all()

@app.get("/api/v2/dovizler/{id}", response_model=DovizTuruRead, tags=["Döviz"])
def doviz_getir(id: int, db: Session = Depends(get_db)):
    return get_or_404(db, DovizTuru, id)

@app.post("/api/v2/dovizler", response_model=DovizTuruRead, status_code=201, tags=["Döviz"])
def doviz_olustur(payload: DovizTuruCreate, db: Session = Depends(get_db)):
    obj = DovizTuru(**payload.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj

@app.put("/api/v2/dovizler/{id}", response_model=DovizTuruRead, tags=["Döviz"])
def doviz_guncelle(id: int, payload: DovizTuruCreate, db: Session = Depends(get_db)):
    obj = get_or_404(db, DovizTuru, id)
    for k, v in payload.model_dump().items(): setattr(obj, k, v)
    db.commit(); db.refresh(obj); return obj


# ════════════════════════════════════════════════════════════
#  BANKA HESAP  /api/v2/banka-hesaplari
# ════════════════════════════════════════════════════════════

@app.get("/api/v2/banka-hesaplari", response_model=List[BankaHesapRead], tags=["Banka"])
def banka_hesaplari_listele(sirket_id: Optional[int] = Query(None), aktif: Optional[bool] = Query(None), db: Session = Depends(get_db)):
    q = db.query(BankaHesap)
    if sirket_id: q = q.filter_by(sirket_id=sirket_id)
    if aktif is not None: q = q.filter(BankaHesap.aktif == aktif)
    return q.order_by(BankaHesap.kod).all()

@app.get("/api/v2/banka-hesaplari/{id}", response_model=BankaHesapRead, tags=["Banka"])
def banka_hesap_getir(id: int, db: Session = Depends(get_db)):
    return get_or_404(db, BankaHesap, id)

@app.get("/api/v2/banka-hesaplari/{id}/bakiye", tags=["Banka"])
def banka_bakiye(id: int, db: Session = Depends(get_db)):
    get_or_404(db, BankaHesap, id)
    giris = float(db.query(func.sum(BankaHareket.tutar)).filter_by(banka_hesap_id=id, yon='GIRIS').scalar() or 0)
    cikis = float(db.query(func.sum(BankaHareket.tutar)).filter_by(banka_hesap_id=id, yon='CIKIS').scalar() or 0)
    return {"hesap_id": id, "giris": giris, "cikis": cikis, "bakiye": round(giris - cikis, 2)}

@app.post("/api/v2/banka-hesaplari", response_model=BankaHesapRead, status_code=201, tags=["Banka"])
def banka_hesap_olustur(payload: BankaHesapCreate, db: Session = Depends(get_db)):
    obj = BankaHesap(**payload.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj

@app.put("/api/v2/banka-hesaplari/{id}", response_model=BankaHesapRead, tags=["Banka"])
def banka_hesap_guncelle(id: int, payload: BankaHesapCreate, db: Session = Depends(get_db)):
    obj = get_or_404(db, BankaHesap, id)
    for k, v in payload.model_dump().items(): setattr(obj, k, v)
    db.commit(); db.refresh(obj); return obj

@app.delete("/api/v2/banka-hesaplari/{id}", tags=["Banka"])
def banka_hesap_sil(id: int, db: Session = Depends(get_db)):
    obj = get_or_404(db, BankaHesap, id); obj.aktif = False; db.commit()
    return {"ok": True, "mesaj": "Banka hesabı pasife alındı"}


# ── Banka Hareket ────────────────────────────────────────────

@app.get("/api/v2/banka-hareketler", response_model=List[BankaHareketRead], tags=["Banka"])
def banka_hareketler_listele(
    hesap_id: Optional[int] = Query(None),
    yon: Optional[str] = Query(None),
    tarih_baslangic: Optional[date] = Query(None),
    tarih_bitis: Optional[date] = Query(None),
    db: Session = Depends(get_db)
):
    q = db.query(BankaHareket)
    if hesap_id: q = q.filter_by(banka_hesap_id=hesap_id)
    if yon: q = q.filter_by(yon=yon.upper())
    if tarih_baslangic: q = q.filter(BankaHareket.tarih >= tarih_baslangic)
    if tarih_bitis: q = q.filter(BankaHareket.tarih <= tarih_bitis)
    return q.order_by(BankaHareket.tarih.desc()).all()

@app.get("/api/v2/banka-hareketler/{id}", response_model=BankaHareketRead, tags=["Banka"])
def banka_hareket_getir(id: int, db: Session = Depends(get_db)):
    return get_or_404(db, BankaHareket, id)

@app.post("/api/v2/banka-hareketler", response_model=BankaHareketRead, status_code=201, tags=["Banka"])
def banka_hareket_olustur(payload: BankaHareketCreate, db: Session = Depends(get_db)):
    obj = BankaHareket(**payload.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj

@app.delete("/api/v2/banka-hareketler/{id}", tags=["Banka"])
def banka_hareket_sil(id: int, db: Session = Depends(get_db)):
    obj = get_or_404(db, BankaHareket, id); db.delete(obj); db.commit()
    return {"ok": True, "mesaj": "Hareket silindi"}


# ════════════════════════════════════════════════════════════
#  KASA HESAP  /api/v2/kasa-hesaplari
# ════════════════════════════════════════════════════════════

@app.get("/api/v2/kasa-hesaplari", response_model=List[KasaHesapRead], tags=["Kasa"])
def kasa_hesaplari_listele(sirket_id: Optional[int] = Query(None), aktif: Optional[bool] = Query(None), db: Session = Depends(get_db)):
    q = db.query(KasaHesap)
    if sirket_id: q = q.filter_by(sirket_id=sirket_id)
    if aktif is not None: q = q.filter(KasaHesap.aktif == aktif)
    return q.order_by(KasaHesap.kod).all()

@app.get("/api/v2/kasa-hesaplari/{id}", response_model=KasaHesapRead, tags=["Kasa"])
def kasa_hesap_getir(id: int, db: Session = Depends(get_db)):
    return get_or_404(db, KasaHesap, id)

@app.get("/api/v2/kasa-hesaplari/{id}/bakiye", tags=["Kasa"])
def kasa_bakiye(id: int, db: Session = Depends(get_db)):
    get_or_404(db, KasaHesap, id)
    giris = float(db.query(func.sum(KasaHareket.tutar)).filter_by(kasa_hesap_id=id, yon='GIRIS').scalar() or 0)
    cikis = float(db.query(func.sum(KasaHareket.tutar)).filter_by(kasa_hesap_id=id, yon='CIKIS').scalar() or 0)
    return {"hesap_id": id, "giris": giris, "cikis": cikis, "bakiye": round(giris - cikis, 2)}

@app.post("/api/v2/kasa-hesaplari", response_model=KasaHesapRead, status_code=201, tags=["Kasa"])
def kasa_hesap_olustur(payload: KasaHesapCreate, db: Session = Depends(get_db)):
    obj = KasaHesap(**payload.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj

@app.put("/api/v2/kasa-hesaplari/{id}", response_model=KasaHesapRead, tags=["Kasa"])
def kasa_hesap_guncelle(id: int, payload: KasaHesapCreate, db: Session = Depends(get_db)):
    obj = get_or_404(db, KasaHesap, id)
    for k, v in payload.model_dump().items(): setattr(obj, k, v)
    db.commit(); db.refresh(obj); return obj

@app.delete("/api/v2/kasa-hesaplari/{id}", tags=["Kasa"])
def kasa_hesap_sil(id: int, db: Session = Depends(get_db)):
    obj = get_or_404(db, KasaHesap, id); obj.aktif = False; db.commit()
    return {"ok": True, "mesaj": "Kasa pasife alındı"}

@app.get("/api/v2/kasa-hareketler", response_model=List[KasaHareketRead], tags=["Kasa"])
def kasa_hareketler_listele(
    hesap_id: Optional[int] = Query(None), yon: Optional[str] = Query(None),
    tarih_baslangic: Optional[date] = Query(None), tarih_bitis: Optional[date] = Query(None),
    db: Session = Depends(get_db)
):
    q = db.query(KasaHareket)
    if hesap_id: q = q.filter_by(kasa_hesap_id=hesap_id)
    if yon: q = q.filter_by(yon=yon.upper())
    if tarih_baslangic: q = q.filter(KasaHareket.tarih >= tarih_baslangic)
    if tarih_bitis: q = q.filter(KasaHareket.tarih <= tarih_bitis)
    return q.order_by(KasaHareket.tarih.desc()).all()

@app.post("/api/v2/kasa-hareketler", response_model=KasaHareketRead, status_code=201, tags=["Kasa"])
def kasa_hareket_olustur(payload: KasaHareketCreate, db: Session = Depends(get_db)):
    obj = KasaHareket(**payload.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj

@app.delete("/api/v2/kasa-hareketler/{id}", tags=["Kasa"])
def kasa_hareket_sil(id: int, db: Session = Depends(get_db)):
    obj = get_or_404(db, KasaHareket, id); db.delete(obj); db.commit()
    return {"ok": True, "mesaj": "Hareket silindi"}


# ════════════════════════════════════════════════════════════
#  CARİ HESAP FİŞİ  /api/v2/cari-fisler
# ════════════════════════════════════════════════════════════

@app.get("/api/v2/cari-fisler", response_model=List[CariHesapFisRead], tags=["Cari Fiş"])
def cari_fisler_listele(sirket_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    q = db.query(CariHesapFis)
    if sirket_id: q = q.filter_by(sirket_id=sirket_id)
    return q.order_by(CariHesapFis.tarih.desc()).all()

@app.get("/api/v2/cari-fisler/{id}", response_model=CariHesapFisRead, tags=["Cari Fiş"])
def cari_fis_getir(id: int, db: Session = Depends(get_db)):
    return get_or_404(db, CariHesapFis, id)

@app.post("/api/v2/cari-fisler", response_model=CariHesapFisRead, status_code=201, tags=["Cari Fiş"])
def cari_fis_olustur(payload: CariHesapFisCreate, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude={"satirlar"})
    fis = CariHesapFis(**data); db.add(fis); db.flush()
    for s in payload.satirlar:
        satir = CariHesapFisSatir(fis_id=fis.id, **s.model_dump())
        db.add(satir)
    db.commit(); db.refresh(fis); return fis

@app.delete("/api/v2/cari-fisler/{id}", tags=["Cari Fiş"])
def cari_fis_sil(id: int, db: Session = Depends(get_db)):
    obj = get_or_404(db, CariHesapFis, id); db.delete(obj); db.commit()
    return {"ok": True, "mesaj": "Fiş silindi"}


# ════════════════════════════════════════════════════════════
#  ÇEK / SENET  /api/v2/cek-senetler
# ════════════════════════════════════════════════════════════

@app.get("/api/v2/cek-senetler", response_model=List[CekSenetRead], tags=["Çek/Senet"])
def cek_senetler_listele(
    sirket_id: Optional[int] = Query(None),
    tip: Optional[str] = Query(None, description="CEK | SENET"),
    yon: Optional[str] = Query(None, description="ALACAK | BORC"),
    durum: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    q = db.query(CekSenet)
    if sirket_id: q = q.filter_by(sirket_id=sirket_id)
    if tip: q = q.filter_by(tip=tip.upper())
    if yon: q = q.filter_by(yon=yon.upper())
    if durum: q = q.filter_by(durum=durum.upper())
    return q.order_by(CekSenet.vade_tarihi).all()

@app.get("/api/v2/cek-senetler/{id}", response_model=CekSenetRead, tags=["Çek/Senet"])
def cek_senet_getir(id: int, db: Session = Depends(get_db)):
    return get_or_404(db, CekSenet, id)

@app.post("/api/v2/cek-senetler", response_model=CekSenetRead, status_code=201, tags=["Çek/Senet"])
def cek_senet_olustur(payload: CekSenetCreate, db: Session = Depends(get_db)):
    obj = CekSenet(**payload.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj

@app.put("/api/v2/cek-senetler/{id}", response_model=CekSenetRead, tags=["Çek/Senet"])
def cek_senet_guncelle(id: int, payload: CekSenetCreate, db: Session = Depends(get_db)):
    obj = get_or_404(db, CekSenet, id)
    for k, v in payload.model_dump().items(): setattr(obj, k, v)
    db.commit(); db.refresh(obj); return obj

@app.delete("/api/v2/cek-senetler/{id}", tags=["Çek/Senet"])
def cek_senet_sil(id: int, db: Session = Depends(get_db)):
    obj = get_or_404(db, CekSenet, id); db.delete(obj); db.commit()
    return {"ok": True, "mesaj": "Çek/Senet silindi"}


# ════════════════════════════════════════════════════════════
#  TAKSİT PLANI  /api/v2/taksitler
# ════════════════════════════════════════════════════════════

@app.get("/api/v2/taksitler", response_model=List[TaksitPlanRead], tags=["Taksit"])
def taksitler_listele(belge_id: Optional[int] = Query(None), odendi: Optional[bool] = Query(None), db: Session = Depends(get_db)):
    q = db.query(TaksitPlan)
    if belge_id: q = q.filter_by(belge_id=belge_id)
    if odendi is not None: q = q.filter(TaksitPlan.odendi == odendi)
    return q.order_by(TaksitPlan.vade_tarihi).all()

@app.post("/api/v2/taksitler", response_model=TaksitPlanRead, status_code=201, tags=["Taksit"])
def taksit_olustur(payload: TaksitPlanCreate, db: Session = Depends(get_db)):
    obj = TaksitPlan(**payload.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj

@app.put("/api/v2/taksitler/{id}/odendi", tags=["Taksit"])
def taksit_odendi_isaretle(id: int, odeme_tarihi: Optional[date] = Query(None), db: Session = Depends(get_db)):
    obj = get_or_404(db, TaksitPlan, id)
    obj.odendi = True; obj.odeme_tarihi = odeme_tarihi or date.today()
    db.commit(); return {"ok": True, "taksit_id": id, "odeme_tarihi": str(obj.odeme_tarihi)}

@app.delete("/api/v2/taksitler/{id}", tags=["Taksit"])
def taksit_sil(id: int, db: Session = Depends(get_db)):
    obj = get_or_404(db, TaksitPlan, id); db.delete(obj); db.commit()
    return {"ok": True, "mesaj": "Taksit silindi"}


# ════════════════════════════════════════════════════════════
#  HESAP GRUBU  /api/v2/hesap-gruplari
# ════════════════════════════════════════════════════════════

@app.get("/api/v2/hesap-gruplari", response_model=List[HesapGrubuRead], tags=["Hesap Grubu"])
def hesap_gruplari_listele(
    tip: Optional[str] = Query(None, description="CARI | STOK"),
    seviye: Optional[int] = Query(None),
    parent_id: Optional[int] = Query(None),
    aktif: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    q = db.query(HesapGrubu)
    if tip: q = q.filter_by(tip=tip.upper())
    if seviye is not None: q = q.filter_by(seviye=seviye)
    if parent_id is not None: q = q.filter_by(parent_id=parent_id)
    if aktif is not None: q = q.filter(HesapGrubu.aktif == aktif)
    return q.order_by(HesapGrubu.seviye, HesapGrubu.kod).all()

@app.get("/api/v2/hesap-gruplari/{id}", response_model=HesapGrubuRead, tags=["Hesap Grubu"])
def hesap_grubu_getir(id: int, db: Session = Depends(get_db)):
    return get_or_404(db, HesapGrubu, id)

@app.post("/api/v2/hesap-gruplari", response_model=HesapGrubuRead, status_code=201, tags=["Hesap Grubu"])
def hesap_grubu_olustur(payload: HesapGrubuCreate, db: Session = Depends(get_db)):
    obj = HesapGrubu(**payload.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj

@app.put("/api/v2/hesap-gruplari/{id}", response_model=HesapGrubuRead, tags=["Hesap Grubu"])
def hesap_grubu_guncelle(id: int, payload: HesapGrubuCreate, db: Session = Depends(get_db)):
    obj = get_or_404(db, HesapGrubu, id)
    for k, v in payload.model_dump().items(): setattr(obj, k, v)
    db.commit(); db.refresh(obj); return obj

@app.delete("/api/v2/hesap-gruplari/{id}", tags=["Hesap Grubu"])
def hesap_grubu_sil(id: int, db: Session = Depends(get_db)):
    obj = get_or_404(db, HesapGrubu, id); obj.aktif = False; db.commit()
    return {"ok": True, "mesaj": "Hesap grubu pasife alındı"}


# ════════════════════════════════════════════════════════════
#  RAPOR  /api/v2/raporlar
# ════════════════════════════════════════════════════════════

@app.get("/api/v2/raporlar", response_model=List[RaporRead], tags=["Rapor"])
def raporlar_listele(kategori: Optional[str] = Query(None), aktif: Optional[bool] = Query(None), db: Session = Depends(get_db)):
    q = db.query(Rapor)
    if kategori: q = q.filter_by(kategori=kategori)
    if aktif is not None: q = q.filter(Rapor.aktif == aktif)
    return q.order_by(Rapor.kategori, Rapor.ad).all()

@app.get("/api/v2/raporlar/{id}", response_model=RaporRead, tags=["Rapor"])
def rapor_getir(id: int, db: Session = Depends(get_db)):
    return get_or_404(db, Rapor, id)

@app.post("/api/v2/raporlar", response_model=RaporRead, status_code=201, tags=["Rapor"])
def rapor_olustur(payload: RaporCreate, db: Session = Depends(get_db)):
    obj = Rapor(**payload.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj

@app.delete("/api/v2/raporlar/{id}", tags=["Rapor"])
def rapor_sil(id: int, db: Session = Depends(get_db)):
    obj = get_or_404(db, Rapor, id); obj.aktif = False; db.commit()
    return {"ok": True, "mesaj": "Rapor pasife alındı"}

@app.get("/api/v2/raporlar/{id}/calistir", tags=["Rapor"])
def rapor_calistir(id: int, db: Session = Depends(get_db)):
    from sqlalchemy import text
    rapor = get_or_404(db, Rapor, id)
    sql = rapor.sql_sorgu.strip()
    if not sql.upper().startswith("SELECT"):
        raise HTTPException(422, "Sadece SELECT sorguları çalıştırılabilir")
    for yasak in ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE"]:
        if yasak in sql.upper():
            raise HTTPException(422, f"'{yasak}' komutu izin verilmiyor")
    try:
        sonuc = db.execute(text(sql))
        kolonlar = list(sonuc.keys())
        satirlar = [dict(zip(kolonlar, row)) for row in sonuc.fetchall()]
        return {"kolonlar": kolonlar, "satirlar": satirlar, "satir_sayisi": len(satirlar)}
    except Exception as e:
        raise HTTPException(500, detail=str(e))


# ════════════════════════════════════════════════════════════
#  ADRES REFERANSLARI  /api/v2/adres
# ════════════════════════════════════════════════════════════

@app.get("/api/v2/adres/ulkeler", response_model=List[UlkeRead], tags=["Adres"])
def ulkeler_listele(db: Session = Depends(get_db)):
    return db.query(Ulke).filter_by(aktif=True).order_by(Ulke.ad).all()

@app.get("/api/v2/adres/iller", response_model=List[IlRead], tags=["Adres"])
def iller_listele(ulke_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    q = db.query(Il).filter_by(aktif=True)
    if ulke_id: q = q.filter_by(ulke_id=ulke_id)
    return q.order_by(Il.ad).all()

@app.get("/api/v2/adres/ilceler", response_model=List[IlceRead], tags=["Adres"])
def ilceler_listele(il_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    q = db.query(Ilce).filter_by(aktif=True)
    if il_id: q = q.filter_by(il_id=il_id)
    return q.order_by(Ilce.ad).all()

@app.get("/api/v2/adres/mahalleler", response_model=List[MahalleRead], tags=["Adres"])
def mahalleler_listele(ilce_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    q = db.query(Mahalle).filter_by(aktif=True)
    if ilce_id: q = q.filter_by(ilce_id=ilce_id)
    return q.order_by(Mahalle.ad).all()


# ════════════════════════════════════════════════════════════
#  CARİ ADRES  /api/v2/cari-adresler
# ════════════════════════════════════════════════════════════

@app.get("/api/v2/cari-adresler", response_model=List[CariAdresRead], tags=["Cari Adres"])
def cari_adresler_listele(cari_id: Optional[int] = Query(None), aktif: Optional[bool] = Query(None), db: Session = Depends(get_db)):
    q = db.query(CariAdres)
    if cari_id: q = q.filter_by(cari_id=cari_id)
    if aktif is not None: q = q.filter(CariAdres.aktif == aktif)
    return q.all()

@app.post("/api/v2/cari-adresler", response_model=CariAdresRead, status_code=201, tags=["Cari Adres"])
def cari_adres_olustur(payload: CariAdresCreate, db: Session = Depends(get_db)):
    obj = CariAdres(**payload.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj

@app.put("/api/v2/cari-adresler/{id}", response_model=CariAdresRead, tags=["Cari Adres"])
def cari_adres_guncelle(id: int, payload: CariAdresCreate, db: Session = Depends(get_db)):
    obj = get_or_404(db, CariAdres, id)
    for k, v in payload.model_dump().items(): setattr(obj, k, v)
    db.commit(); db.refresh(obj); return obj

@app.delete("/api/v2/cari-adresler/{id}", tags=["Cari Adres"])
def cari_adres_sil(id: int, db: Session = Depends(get_db)):
    obj = get_or_404(db, CariAdres, id); obj.aktif = False; db.commit()
    return {"ok": True, "mesaj": "Adres pasife alındı"}


# ════════════════════════════════════════════════════════════
#  CARİ İLETİŞİM  /api/v2/cari-iletisimler
# ════════════════════════════════════════════════════════════

@app.get("/api/v2/cari-iletisimler", response_model=List[CariIletisimRead], tags=["Cari İletişim"])
def cari_iletisimler_listele(cari_id: Optional[int] = Query(None), aktif: Optional[bool] = Query(None), db: Session = Depends(get_db)):
    q = db.query(CariIletisim)
    if cari_id: q = q.filter_by(cari_id=cari_id)
    if aktif is not None: q = q.filter(CariIletisim.aktif == aktif)
    return q.all()

@app.post("/api/v2/cari-iletisimler", response_model=CariIletisimRead, status_code=201, tags=["Cari İletişim"])
def cari_iletisim_olustur(payload: CariIletisimCreate, db: Session = Depends(get_db)):
    obj = CariIletisim(**payload.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj

@app.delete("/api/v2/cari-iletisimler/{id}", tags=["Cari İletişim"])
def cari_iletisim_sil(id: int, db: Session = Depends(get_db)):
    obj = get_or_404(db, CariIletisim, id); obj.aktif = False; db.commit()
    return {"ok": True, "mesaj": "İletişim bilgisi pasife alındı"}


# ════════════════════════════════════════════════════════════
#  CARİ BANKA HESABI  /api/v2/cari-banka-hesaplari
# ════════════════════════════════════════════════════════════

@app.get("/api/v2/cari-banka-hesaplari", response_model=List[CariBankaHesapRead], tags=["Cari Banka"])
def cari_banka_hesaplari_listele(cari_id: Optional[int] = Query(None), aktif: Optional[bool] = Query(None), db: Session = Depends(get_db)):
    q = db.query(CariBankaHesap)
    if cari_id: q = q.filter_by(cari_id=cari_id)
    if aktif is not None: q = q.filter(CariBankaHesap.aktif == aktif)
    return q.all()

@app.post("/api/v2/cari-banka-hesaplari", response_model=CariBankaHesapRead, status_code=201, tags=["Cari Banka"])
def cari_banka_hesap_olustur(payload: CariBankaHesapCreate, db: Session = Depends(get_db)):
    obj = CariBankaHesap(**payload.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj

@app.delete("/api/v2/cari-banka-hesaplari/{id}", tags=["Cari Banka"])
def cari_banka_hesap_sil(id: int, db: Session = Depends(get_db)):
    obj = get_or_404(db, CariBankaHesap, id); obj.aktif = False; db.commit()
    return {"ok": True, "mesaj": "Banka hesabı pasife alındı"}


# ════════════════════════════════════════════════════════════
#  KULLANICI  /api/v2/kullanicilar
# ════════════════════════════════════════════════════════════

@app.get("/api/v2/kullanicilar", response_model=List[KullaniciRead], tags=["Kullanıcı"])
def kullanicilar_listele(aktif: Optional[bool] = Query(None), db: Session = Depends(get_db)):
    q = db.query(Kullanici)
    if aktif is not None: q = q.filter(Kullanici.aktif == aktif)
    return q.order_by(Kullanici.ad_soyad).all()

@app.get("/api/v2/kullanicilar/{id}", response_model=KullaniciRead, tags=["Kullanıcı"])
def kullanici_getir(id: int, db: Session = Depends(get_db)):
    return get_or_404(db, Kullanici, id)

@app.delete("/api/v2/kullanicilar/{id}", tags=["Kullanıcı"])
def kullanici_sil(id: int, db: Session = Depends(get_db)):
    obj = get_or_404(db, Kullanici, id); obj.aktif = False; db.commit()
    return {"ok": True, "mesaj": "Kullanıcı devre dışı bırakıldı"}

@app.get("/api/v2/kullanicilar/{id}/yetkiler", tags=["Kullanıcı"])
def kullanici_yetkiler(id: int, db: Session = Depends(get_db)):
    get_or_404(db, Kullanici, id)
    sirket = [y.sirket_id for y in db.query(KullaniciSirketYetki).filter_by(kullanici_id=id).all()]
    depo   = [y.depo_id   for y in db.query(KullaniciDepoYetki).filter_by(kullanici_id=id).all()]
    belge  = [{"belge_tip": y.belge_tip, "cari_tip": y.cari_tip, "yazma": y.yazma}
              for y in db.query(KullaniciBelgeYetki).filter_by(kullanici_id=id).all()]
    return {"kullanici_id": id, "sirket_yetkileri": sirket, "depo_yetkileri": depo, "belge_yetkileri": belge}


# ════════════════════════════════════════════════════════════
#  v1 ENDPOINT'LERİ (geriye dönük uyum)
# ════════════════════════════════════════════════════════════

@app.get("/api/v1/birim-gruplari", response_model=List[BirimGrubuRead], tags=["v1 - Birim"])
def bg_listele(aktif: Optional[bool] = Query(None), db: Session = Depends(get_db)):
    q = db.query(BirimGrubu)
    if aktif is not None: q = q.filter(BirimGrubu.aktif == aktif)
    return q.order_by(BirimGrubu.ad).all()

@app.get("/api/v1/birim-gruplari/{id}", response_model=BirimGrubuRead, tags=["v1 - Birim"])
def bg_getir(id: int, db: Session = Depends(get_db)): return get_or_404(db, BirimGrubu, id)

@app.post("/api/v1/birim-gruplari", response_model=BirimGrubuRead, status_code=201, tags=["v1 - Birim"])
def bg_olustur(p: BirimGrubuCreate, db: Session = Depends(get_db)):
    obj = BirimGrubu(**p.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj

@app.put("/api/v1/birim-gruplari/{id}", response_model=BirimGrubuRead, tags=["v1 - Birim"])
def bg_guncelle(id: int, p: BirimGrubuCreate, db: Session = Depends(get_db)):
    obj = get_or_404(db, BirimGrubu, id)
    for k, v in p.model_dump().items(): setattr(obj, k, v)
    db.commit(); db.refresh(obj); return obj

@app.delete("/api/v1/birim-gruplari/{id}", tags=["v1 - Birim"])
def bg_sil(id: int, db: Session = Depends(get_db)):
    obj = get_or_404(db, BirimGrubu, id); obj.aktif = False; db.commit(); return {"ok": True}

@app.get("/api/v1/birimler", response_model=List[BirimRead], tags=["v1 - Birim"])
def b_listele(grup_id: Optional[int] = Query(None), aktif: Optional[bool] = Query(None), db: Session = Depends(get_db)):
    q = db.query(Birim)
    if grup_id: q = q.filter_by(grup_id=grup_id)
    if aktif is not None: q = q.filter(Birim.aktif == aktif)
    return q.order_by(Birim.kod).all()

@app.get("/api/v1/birimler/{id}", response_model=BirimRead, tags=["v1 - Birim"])
def b_getir(id: int, db: Session = Depends(get_db)): return get_or_404(db, Birim, id)

@app.post("/api/v1/birimler", response_model=BirimRead, status_code=201, tags=["v1 - Birim"])
def b_olustur(p: BirimCreate, db: Session = Depends(get_db)):
    obj = Birim(**p.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj

@app.put("/api/v1/birimler/{id}", response_model=BirimRead, tags=["v1 - Birim"])
def b_guncelle(id: int, p: BirimCreate, db: Session = Depends(get_db)):
    obj = get_or_404(db, Birim, id)
    for k, v in p.model_dump().items(): setattr(obj, k, v)
    db.commit(); db.refresh(obj); return obj

@app.delete("/api/v1/birimler/{id}", tags=["v1 - Birim"])
def b_sil(id: int, db: Session = Depends(get_db)):
    obj = get_or_404(db, Birim, id); obj.aktif = False; db.commit(); return {"ok": True}

@app.get("/api/v1/birim-donusumleri", response_model=List[BirimDonusumRead], tags=["v1 - Birim"])
def bd_listele(aktif: Optional[bool] = Query(None), db: Session = Depends(get_db)):
    q = db.query(BirimDonusum)
    if aktif is not None: q = q.filter(BirimDonusum.aktif == aktif)
    return q.all()

@app.post("/api/v1/birim-donusumleri", response_model=BirimDonusumRead, status_code=201, tags=["v1 - Birim"])
def bd_olustur(p: BirimDonusumCreate, db: Session = Depends(get_db)):
    obj = BirimDonusum(**p.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj

@app.get("/api/v1/birim-cevirme", tags=["v1 - Birim"])
def birim_cevirme(kaynak_id: int, hedef_id: int, miktar: float = 1.0, db: Session = Depends(get_db)):
    if kaynak_id == hedef_id:
        return {"ok": True, "katsayi": 1.0, "sonuc": round(miktar, 6)}
    kaynak = db.get(Birim, kaynak_id); hedef = db.get(Birim, hedef_id)
    if not kaynak or not hedef:
        raise HTTPException(404, "Birim bulunamadı")
    ozel = db.query(BirimDonusum).filter_by(kaynak_birim_id=kaynak_id, hedef_birim_id=hedef_id, aktif=True).first()
    if ozel:
        k = float(ozel.carpan); return {"ok": True, "katsayi": k, "sonuc": round(miktar * k, 6)}
    ters = db.query(BirimDonusum).filter_by(kaynak_birim_id=hedef_id, hedef_birim_id=kaynak_id, aktif=True).first()
    if ters:
        k = 1.0 / float(ters.carpan); return {"ok": True, "katsayi": k, "sonuc": round(miktar * k, 6)}
    if kaynak.grup_id == hedef.grup_id:
        k = float(kaynak.katsayi) / float(hedef.katsayi)
        return {"ok": True, "katsayi": k, "sonuc": round(miktar * k, 6)}
    raise HTTPException(422, "Bu birimler arasında çevrim tanımlı değil")

@app.get("/api/v1/cariler", response_model=List[CariRead], tags=["v1 - Cari"])
def c_listele(tip: Optional[str] = Query(None), aktif: Optional[bool] = Query(None), sehir: Optional[str] = Query(None), db: Session = Depends(get_db)):
    q = db.query(Cari)
    if aktif is not None: q = q.filter(Cari.aktif == aktif)
    if tip: q = q.filter(Cari.tip.in_([tip, "HER_IKISI"]))
    if sehir: q = q.filter(Cari.sehir.ilike(f"%{sehir}%"))
    return q.order_by(Cari.unvan).all()

@app.get("/api/v1/cariler/{id}", response_model=CariRead, tags=["v1 - Cari"])
def c_getir(id: int, db: Session = Depends(get_db)): return get_or_404(db, Cari, id)

@app.get("/api/v1/cariler/{id}/bakiye", tags=["v1 - Cari"])
def c_bakiye(id: int, db: Session = Depends(get_db)):
    if not db.get(Cari, id): raise HTTPException(404, "Cari bulunamadı")
    borc   = float(db.query(func.sum(CariHareket.tutar)).filter_by(cari_id=id, hareket_tipi="BORC").scalar() or 0)
    alacak = float(db.query(func.sum(CariHareket.tutar)).filter_by(cari_id=id, hareket_tipi="ALACAK").scalar() or 0)
    return {"cari_id": id, "borc": borc, "alacak": alacak, "bakiye": borc - alacak}

@app.post("/api/v1/cariler", response_model=CariRead, status_code=201, tags=["v1 - Cari"])
def c_olustur(p: CariCreate, db: Session = Depends(get_db)):
    obj = Cari(**p.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj

@app.put("/api/v1/cariler/{id}", response_model=CariRead, tags=["v1 - Cari"])
def c_guncelle(id: int, p: CariCreate, db: Session = Depends(get_db)):
    obj = get_or_404(db, Cari, id)
    for k, v in p.model_dump().items(): setattr(obj, k, v)
    db.commit(); db.refresh(obj); return obj

@app.delete("/api/v1/cariler/{id}", tags=["v1 - Cari"])
def c_sil(id: int, db: Session = Depends(get_db)):
    obj = get_or_404(db, Cari, id); obj.aktif = False; db.commit(); return {"ok": True}

@app.get("/api/v1/cari-hareketler", response_model=List[CariHareketRead], tags=["v1 - Cari"])
def ch_listele(cari_id: Optional[int]=Query(None), hareket_tipi: Optional[str]=Query(None), tarih_baslangic: Optional[date]=Query(None), tarih_bitis: Optional[date]=Query(None), db: Session=Depends(get_db)):
    q = db.query(CariHareket)
    if cari_id: q = q.filter_by(cari_id=cari_id)
    if hareket_tipi: q = q.filter_by(hareket_tipi=hareket_tipi)
    if tarih_baslangic: q = q.filter(CariHareket.tarih >= tarih_baslangic)
    if tarih_bitis: q = q.filter(CariHareket.tarih <= tarih_bitis)
    return q.order_by(CariHareket.tarih.desc()).all()

@app.post("/api/v1/cari-hareketler", response_model=CariHareketRead, status_code=201, tags=["v1 - Cari"])
def ch_olustur(p: CariHareketCreate, db: Session = Depends(get_db)):
    obj = CariHareket(**p.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj

@app.delete("/api/v1/cari-hareketler/{id}", tags=["v1 - Cari"])
def ch_sil(id: int, db: Session = Depends(get_db)):
    obj = get_or_404(db, CariHareket, id); db.delete(obj); db.commit(); return {"ok": True}

@app.get("/api/v1/stoklar", response_model=List[StokKartiRead], tags=["v1 - Stok"])
def s_listele(tip: Optional[str]=Query(None), aktif: Optional[bool]=Query(None), db: Session=Depends(get_db)):
    q = db.query(StokKarti)
    if tip: q = q.filter_by(tip=tip)
    if aktif is not None: q = q.filter(StokKarti.aktif == aktif)
    return q.order_by(StokKarti.ad).all()

@app.get("/api/v1/stoklar/{id}", response_model=StokKartiRead, tags=["v1 - Stok"])
def s_getir(id: int, db: Session = Depends(get_db)): return get_or_404(db, StokKarti, id)

@app.get("/api/v1/stoklar/{id}/miktar", tags=["v1 - Stok"])
def s_miktar(id: int, db: Session = Depends(get_db)):
    obj = get_or_404(db, StokKarti, id)
    if obj.tip == "HIZMET": return {"stok_id": id, "tip": "HIZMET", "miktar": None}
    giris = float(db.query(func.sum(StokHareket.miktar)).filter_by(stok_id=id, hareket_tipi="GIRIS").scalar() or 0)
    cikis = float(db.query(func.sum(StokHareket.miktar)).filter_by(stok_id=id, hareket_tipi="CIKIS").scalar() or 0)
    return {"stok_id": id, "tip": "MALZEME", "miktar": giris - cikis}

@app.post("/api/v1/stoklar", response_model=StokKartiRead, status_code=201, tags=["v1 - Stok"])
def s_olustur(p: StokKartiCreate, db: Session = Depends(get_db)):
    obj = StokKarti(**p.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj

@app.put("/api/v1/stoklar/{id}", response_model=StokKartiRead, tags=["v1 - Stok"])
def s_guncelle(id: int, p: StokKartiCreate, db: Session = Depends(get_db)):
    obj = get_or_404(db, StokKarti, id)
    for k, v in p.model_dump().items(): setattr(obj, k, v)
    db.commit(); db.refresh(obj); return obj

@app.delete("/api/v1/stoklar/{id}", tags=["v1 - Stok"])
def s_sil(id: int, db: Session = Depends(get_db)):
    obj = get_or_404(db, StokKarti, id); obj.aktif = False; db.commit(); return {"ok": True}

@app.get("/api/v1/stok-hareketler", response_model=List[StokHareketRead], tags=["v1 - Stok"])
def sh_listele(stok_id: Optional[int]=Query(None), hareket_tipi: Optional[str]=Query(None), tarih_baslangic: Optional[date]=Query(None), tarih_bitis: Optional[date]=Query(None), db: Session=Depends(get_db)):
    q = db.query(StokHareket)
    if stok_id: q = q.filter_by(stok_id=stok_id)
    if hareket_tipi: q = q.filter_by(hareket_tipi=hareket_tipi)
    if tarih_baslangic: q = q.filter(StokHareket.tarih >= tarih_baslangic)
    if tarih_bitis: q = q.filter(StokHareket.tarih <= tarih_bitis)
    return q.order_by(StokHareket.tarih.desc()).all()

@app.post("/api/v1/stok-hareketler", response_model=StokHareketRead, status_code=201, tags=["v1 - Stok"])
def sh_olustur(p: StokHareketCreate, db: Session = Depends(get_db)):
    obj = StokHareket(**p.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj

@app.delete("/api/v1/stok-hareketler/{id}", tags=["v1 - Stok"])
def sh_sil(id: int, db: Session = Depends(get_db)):
    obj = get_or_404(db, StokHareket, id); db.delete(obj); db.commit(); return {"ok": True}

@app.get("/api/v1/belgeler", tags=["v1 - Belge"])
def bel_listele(belge_tip: Optional[str]=Query(None), cari_tip: Optional[str]=Query(None), durum: Optional[str]=Query(None), cari_id: Optional[int]=Query(None), sirket_id: Optional[int]=Query(None), tarih_baslangic: Optional[date]=Query(None), tarih_bitis: Optional[date]=Query(None), limit: int=Query(100, le=500), db: Session=Depends(get_db)):
    q = db.query(BelgeBaslik)
    if belge_tip: q = q.filter_by(belge_tip=belge_tip.upper())
    if cari_tip: q = q.filter_by(cari_tip=cari_tip.upper())
    if durum: q = q.filter_by(durum=durum.upper())
    if cari_id: q = q.filter_by(cari_id=cari_id)
    if sirket_id: q = q.filter_by(sirket_id=sirket_id)
    if tarih_baslangic: q = q.filter(BelgeBaslik.tarih >= tarih_baslangic)
    if tarih_bitis: q = q.filter(BelgeBaslik.tarih <= tarih_bitis)
    return [BelgeBaslikRead.from_orm_obj(b) for b in q.order_by(BelgeBaslik.tarih.desc()).limit(limit).all()]

@app.get("/api/v1/belgeler/{id}", tags=["v1 - Belge"])
def bel_getir(id: int, db: Session = Depends(get_db)):
    return BelgeBaslikRead.from_orm_obj(get_or_404(db, BelgeBaslik, id))

@app.post("/api/v1/belgeler", status_code=201, tags=["v1 - Belge"])
def bel_olustur(p: BelgeBaslikCreate, db: Session = Depends(get_db)):
    data = p.model_dump(exclude={"satirlar"})
    baslik = BelgeBaslik(**data); db.add(baslik); db.flush()
    for s in p.satirlar:
        db.add(BelgeSatir(baslik_id=baslik.id, **s.model_dump()))
    db.commit(); db.refresh(baslik); return BelgeBaslikRead.from_orm_obj(baslik)

@app.put("/api/v1/belgeler/{id}", tags=["v1 - Belge"])
def bel_guncelle(id: int, p: BelgeBaslikCreate, db: Session = Depends(get_db)):
    baslik = get_or_404(db, BelgeBaslik, id)
    for k, v in p.model_dump(exclude={"satirlar"}).items(): setattr(baslik, k, v)
    db.query(BelgeSatir).filter_by(baslik_id=id).delete(); db.flush()
    for s in p.satirlar:
        db.add(BelgeSatir(baslik_id=id, **s.model_dump()))
    db.commit(); db.refresh(baslik); return BelgeBaslikRead.from_orm_obj(baslik)

@app.delete("/api/v1/belgeler/{id}", tags=["v1 - Belge"])
def bel_sil(id: int, db: Session = Depends(get_db)):
    obj = get_or_404(db, BelgeBaslik, id)
    db.query(CariHareket).filter_by(kaynak_tip="FATURA", kaynak_id=id).delete()
    db.query(StokHareket).filter(StokHareket.belge_no == obj.belge_no).delete()
    db.delete(obj); db.commit(); return {"ok": True}

@app.get("/api/v1/belge-satirlari", response_model=List[BelgeSatirRead], tags=["v1 - Belge"])
def bsat_listele(baslik_id: Optional[int]=Query(None), stok_id: Optional[int]=Query(None), db: Session=Depends(get_db)):
    q = db.query(BelgeSatir)
    if baslik_id: q = q.filter_by(baslik_id=baslik_id)
    if stok_id: q = q.filter_by(stok_id=stok_id)
    return q.order_by(BelgeSatir.baslik_id, BelgeSatir.sira_no).all()

@app.get("/api/v1/ozet", tags=["v1 - Genel"])
def ozet_v1(db: Session = Depends(get_db)):
    return {
        "cari_sayisi":  db.query(func.count(Cari.id)).filter_by(aktif=True).scalar(),
        "stok_sayisi":  db.query(func.count(StokKarti.id)).filter_by(aktif=True).scalar(),
        "birim_sayisi": db.query(func.count(Birim.id)).filter_by(aktif=True).scalar(),
        "acik_fatura":  db.query(func.count(BelgeBaslik.id)).filter_by(belge_tip="FATURA", durum="ACIK").scalar(),
        "acik_siparis": db.query(func.count(BelgeBaslik.id)).filter_by(belge_tip="SIPARIS", durum="ACIK").scalar(),
    }


# ════════════════════════════════════════════════════════════
#  ÇALIŞTIRMA
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
