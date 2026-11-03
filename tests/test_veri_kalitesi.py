#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
İstanbul Barajları Veri Kalitesi ve Bütünlük Testleri (Data Quality Tests)
==========================================================================
Veri setlerindeki tarih sürekliliğini, tekilliğini (primary key),
değer aralıklarını ve türetilmiş tabloların tutarlılığını doğrular.
"""

from pathlib import Path
import unittest
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent


class TestVeriKalitesi(unittest.TestCase):
    """Ham ve işlenmiş veri setleri için kalite kontrol testleri."""

    @classmethod
    def setUpClass(cls):
        cls.df_occ = pd.read_csv(BASE_DIR / "dam_occupancy.csv")
        cls.df_xl = pd.read_excel(
            BASE_DIR / "istanbul-barajlarnda-ya-ve-gunluk-tuketim-verileri.xlsx",
            sheet_name="Sayfa1",
        )
        cls.df_merged = pd.read_csv(BASE_DIR / "data" / "istanbul_baraj_birlesik_veri.csv")
        cls.df_unpivot = pd.read_csv(BASE_DIR / "data" / "istanbul_baraj_yagis_unpivot.csv")

    def test_doluluk_verisi_tekillik_ve_sureklilik(self):
        """dam_occupancy.csv içinde mükerrer veya eksik gün olmamalıdır."""
        self.assertEqual(self.df_occ.isnull().sum().sum(), 0, "Boş (NaN) değer bulunmamalı.")
        self.assertEqual(
            self.df_occ["DATE"].duplicated().sum(),
            0,
            "DATE sütununda mükerrer tarih bulunmamalı (Primary Key ihlali).",
        )
        dt = pd.to_datetime(self.df_occ["DATE"])
        beklenen_gun_sayisi = (dt.max() - dt.min()).days + 1
        self.assertEqual(
            len(self.df_occ),
            beklenen_gun_sayisi,
            "Tarih serisinde atlanmış/eksik gün bulunmamalı.",
        )

    def test_doluluk_orani_deger_araligi(self):
        """Doluluk oranı %0 ile %100 arasında, rezerv su pozitif olmalıdır."""
        oran = self.df_occ["GENERAL_DAM_OCCUPANCY_RATE"]
        rezerv = self.df_occ["GENERAL_DAM_RESERVED_WATER"]
        self.assertTrue(((oran >= 0) & (oran <= 100)).all(), "Doluluk oranı 0-100 aralığında olmalı.")
        self.assertTrue((rezerv > 0).all(), "Rezerv su miktarı pozitif olmalı.")

    def test_excel_yapisi_ve_temizligi(self):
        """Excel dosyasında Unnamed (boş) sütun ve negatif değer bulunmamalıdır."""
        unnamed_cols = [c for c in self.df_xl.columns if str(c).startswith("Unnamed")]
        self.assertEqual(len(unnamed_cols), 0, f"Boş sütun kalmamalı: {unnamed_cols}")
        self.assertEqual(self.df_xl.isnull().sum().sum(), 0, "Excel verisinde NaN değer olmamalı.")
        self.assertEqual(len(self.df_xl), 4797, "Excel satır sayısı 4797 gün olmalı.")

    def test_birlesik_ve_unpivot_veri_tutarliligi(self):
        """Türetilmiş CSV dosyalarının boyut ve şemaları tutarlı olmalıdır."""
        self.assertEqual(len(self.df_merged), 4797)
        self.assertEqual(
            len(self.df_unpivot),
            len(self.df_merged) * 10,
            "Unpivot tablosu 10 baraj x 4797 gün = 47.970 satır olmalıdır.",
        )
        self.assertEqual(self.df_unpivot["Baraj_Adi"].nunique(), 10, "10 benzersiz baraj bulunmalı.")
        self.assertTrue((self.df_unpivot["Yagis_mm"] >= 0).all(), "Yağış değerleri negatif olamaz.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
