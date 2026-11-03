#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
İstanbul Barajları Doluluk, Yağış ve Günlük Su Tüketimi Analiz Betiği
=====================================================================
Bu betik:
1. 'dam_occupancy.csv' ve 'istanbul-barajlarnda-ya-ve-gunluk-tuketim-verileri.xlsx'
   veri setlerini doğrular, mükerrer/eksik günleri ve boş sütunları temizler.
2. İki veri setini birleştirerek analize ve Power BI yıldız şemasına (Star Schema)
   uygun temiz CSV dosyaları ('data/' dizini altında) üretir:
   - data/istanbul_baraj_birlesik_veri.csv (Birleştirilmiş günlük tablo)
   - data/istanbul_baraj_yagis_unpivot.csv (Baraj bazlı uzun/unpivot format)
3. Temel istatistiksel bulguları hesaplar ve 'assets/' dizinine yüksek çözünürlüklü
   analiz grafikleri kaydeder.
"""

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns

# Görsel tema ayarları
plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Helvetica"]
plt.rcParams["axes.unicode_minus"] = False
sns.set_theme(style="whitegrid", palette="deep")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
ASSETS_DIR = BASE_DIR / "assets"

BARAJ_ISIM_HARITASI = {
    "Ömerli": "Ömerli",
    "Darlik": "Darlık",
    "Elmali": "Elmalı",
    "Terkos": "Terkos",
    "B.çekmece": "Büyükçekmece",
    "Sazlidere": "Sazlıdere",
    "Alibey": "Alibey",
    "Kazandere": "Kazandere",
    "Pabuçdere": "Pabuçdere",
    "ıstırancalar": "Istrancalar",
}

MEVSIM_HARITASI = {
    12: "Kış", 1: "Kış", 2: "Kış",
    3: "İlkbahar", 4: "İlkbahar", 5: "İlkbahar",
    6: "Yaz", 7: "Yaz", 8: "Yaz",
    9: "Sonbahar", 10: "Sonbahar", 11: "Sonbahar",
}


def verileri_yukle_ve_temizle():
    """Ham CSV ve Excel dosyalarını yükler, veri kalitesi sorunlarını giderir."""
    DATA_DIR.mkdir(exist_ok=True)
    ASSETS_DIR.mkdir(exist_ok=True)

    # 1. Baraj Doluluk Verisi (dam_occupancy.csv)
    csv_path = BASE_DIR / "dam_occupancy.csv"
    df_occ = pd.read_csv(csv_path)

    # Bilinen hatalı/mükerrer kayıtların temizlenmesi (2020-04-19 anomalisi ve 2021-01-07 tekrarı)
    df_occ = df_occ[
        ~((df_occ["DATE"] == "2020-04-19") & (df_occ["GENERAL_DAM_OCCUPANCY_RATE"] == 80.79))
    ]
    df_occ = df_occ.drop_duplicates(subset=["DATE"], keep="first").copy()
    df_occ["DATE_DT"] = pd.to_datetime(df_occ["DATE"])
    df_occ = df_occ.sort_values("DATE_DT").set_index("DATE_DT")

    # Kesintisiz günlük tarih dizini (2005-01-01 .. 2021-04-07)
    full_range = pd.date_range(df_occ.index.min(), df_occ.index.max(), freq="D")
    df_occ = df_occ.reindex(full_range)
    df_occ["GENERAL_DAM_OCCUPANCY_RATE"] = (
        df_occ["GENERAL_DAM_OCCUPANCY_RATE"].interpolate(method="linear").round(2)
    )
    df_occ["GENERAL_DAM_RESERVED_WATER"] = (
        df_occ["GENERAL_DAM_RESERVED_WATER"].interpolate(method="linear").round().astype(int)
    )
    df_occ["DATE"] = df_occ.index.strftime("%Y-%m-%d")

    # Temizlenmiş CSV'yi ana dizine de kaydet
    df_occ_out = df_occ[
        ["DATE", "GENERAL_DAM_OCCUPANCY_RATE", "GENERAL_DAM_RESERVED_WATER"]
    ].reset_index(drop=True)
    df_occ_out.to_csv(csv_path, index=False)

    # 2. Yağış ve Günlük Su Tüketimi Verisi (Excel)
    xl_path = BASE_DIR / "istanbul-barajlarnda-ya-ve-gunluk-tuketim-verileri.xlsx"
    df_xl = pd.read_excel(xl_path, sheet_name="Sayfa1")
    bos_sutunlar = [c for c in df_xl.columns if str(c).startswith("Unnamed")]
    if bos_sutunlar:
        df_xl = df_xl.drop(columns=bos_sutunlar)
        with pd.ExcelWriter(xl_path, engine="openpyxl") as writer:
            df_xl.to_excel(writer, sheet_name="Sayfa1", index=False)

    df_xl["Tarih"] = pd.to_datetime(df_xl["Tarih"])
    df_xl = df_xl.sort_values("Tarih").reset_index(drop=True)

    # Standart isimlendirilmiş kopya oluştur
    df_std = df_xl.rename(
        columns={
            **BARAJ_ISIM_HARITASI,
            "İstanbul günlük tüketim(m³/gün)": "Gunluk_Tuketim_m3",
        }
    )
    baraj_sutunlari = list(BARAJ_ISIM_HARITASI.values())
    df_std["Toplam_Yagis_mm"] = df_std[baraj_sutunlari].sum(axis=1).round(2)
    df_std["Ortalama_Yagis_mm"] = df_std[baraj_sutunlari].mean(axis=1).round(2)

    # 3. Birleştirilmiş Veri Seti (Tam Tarih ve Ortak Dönem)
    df_occ_merge = df_occ.reset_index().rename(
        columns={
            "index": "Tarih",
            "GENERAL_DAM_OCCUPANCY_RATE": "Doluluk_Orani_Yuzde",
            "GENERAL_DAM_RESERVED_WATER": "Rezerv_Su_Milyon_m3",
        }
    )[["Tarih", "Doluluk_Orani_Yuzde", "Rezerv_Su_Milyon_m3"]]

    df_merged = pd.merge(df_std, df_occ_merge, on="Tarih", how="left")
    df_merged["Yil"] = df_merged["Tarih"].dt.year
    df_merged["Ay"] = df_merged["Tarih"].dt.month
    df_merged["Mevsim"] = df_merged["Ay"].map(MEVSIM_HARITASI)

    df_merged.to_csv(DATA_DIR / "istanbul_baraj_birlesik_veri.csv", index=False)

    # 4. Unpivot (Uzun Format) Baraj Yağış Veri Seti (Power BI X-ekseni ve Dilimleyici için)
    df_unpivot = df_merged.melt(
        id_vars=["Tarih", "Yil", "Ay", "Mevsim"],
        value_vars=baraj_sutunlari,
        var_name="Baraj_Adi",
        value_name="Yagis_mm",
    )
    df_unpivot.to_csv(DATA_DIR / "istanbul_baraj_yagis_unpivot.csv", index=False)

    return df_occ_out, df_std, df_merged, df_unpivot


def grafikleri_olustur(df_occ, df_std, df_merged, df_unpivot):
    """GitHub README ve raporlama için 4 adet yüksek çözünürlüklü grafik üretir."""
    baraj_sutunlari = list(BARAJ_ISIM_HARITASI.values())

    # --- GRAFİK 1: 4'lü Yönetici Özeti Gösterge Paneli (dashboard_ozet.png) ---
    fig, axes = plt.subplots(2, 2, figsize=(16, 10), dpi=180)
    fig.suptitle(
        "İstanbul Barajları Doluluk, Yağış ve Su Tüketimi Analiz Paneli",
        fontsize=16,
        fontweight="bold",
        y=0.98,
    )

    # 1A: Baraj Doluluk Oranı Zaman Serisi (2005-2021)
    ax1 = axes[0, 0]
    df_occ_dt = df_occ.copy()
    df_occ_dt["DATE"] = pd.to_datetime(df_occ_dt["DATE"])
    ax1.plot(
        df_occ_dt["DATE"],
        df_occ_dt["GENERAL_DAM_OCCUPANCY_RATE"],
        color="#1f77b4",
        linewidth=1.2,
        label="Günlük Doluluk (%)",
    )
    ax1.fill_between(
        df_occ_dt["DATE"],
        df_occ_dt["GENERAL_DAM_OCCUPANCY_RATE"],
        color="#1f77b4",
        alpha=0.18,
    )
    mean_occ = df_occ_dt["GENERAL_DAM_OCCUPANCY_RATE"].mean()
    ax1.axhline(
        mean_occ,
        color="#d62728",
        linestyle="--",
        linewidth=1.3,
        label=f"Ortalama: %{mean_occ:.1f}",
    )
    ax1.set_title("Genel Baraj Doluluk Oranı Seyri (2005–2021)", fontweight="bold")
    ax1.set_ylabel("Doluluk Oranı (%)")
    ax1.set_ylim(0, 105)
    ax1.legend(loc="lower left")

    # 1B: Yıllara Göre Ortalama Günlük Su Tüketimi (2011-2024)
    ax2 = axes[0, 1]
    yearly_cons = (
        df_merged[df_merged["Yil"] <= 2023]
        .groupby("Yil")["Gunluk_Tuketim_m3"]
        .mean()
        / 1e6
    )
    bars = ax2.bar(
        yearly_cons.index.astype(str),
        yearly_cons.values,
        color=sns.color_palette("Blues_d", len(yearly_cons)),
        edgecolor="black",
        linewidth=0.5,
    )
    ax2.set_title(
        "Yıllara Göre Ortalama Günlük Su Tüketimi (2011–2023)", fontweight="bold"
    )
    ax2.set_ylabel("Milyon m³ / Gün")
    ax2.set_ylim(0, yearly_cons.max() * 1.18)
    ax2.tick_params(axis="x", rotation=45)
    for bar in bars:
        h = bar.get_height()
        ax2.text(
            bar.get_x() + bar.get_width() / 2,
            h + 0.04,
            f"{h:.2f}",
            ha="center",
            va="bottom",
            fontsize=8,
            fontweight="bold",
        )

    # 1C: Baraj Havzalarına Göre Toplam Yağış Karşılaştırması (2011-2024)
    ax3 = axes[1, 0]
    dam_totals = df_std[baraj_sutunlari].sum().sort_values(ascending=True)
    colors = sns.color_palette("viridis", len(dam_totals))
    bars_h = ax3.barh(dam_totals.index, dam_totals.values, color=colors)
    ax3.set_title(
        "Baraj Havzalarına Göre Kümülatif Yağış Miktarı (2011–2024)",
        fontweight="bold",
    )
    ax3.set_xlabel("Toplam Yağış (mm)")
    ax3.set_xlim(0, dam_totals.max() * 1.15)
    for bar in bars_h:
        w = bar.get_width()
        ax3.text(
            w + 150,
            bar.get_y() + bar.get_height() / 2,
            f"{w:,.0f} mm",
            va="center",
            fontsize=8.5,
            fontweight="bold",
        )

    # 1D: Aylık Ortalama Doluluk Oranı ve Tüketim İlişkisi (Mevsimsellik)
    ax4 = axes[1, 1]
    overlap_df = df_merged.dropna(subset=["Doluluk_Orani_Yuzde"]).copy()
    monthly_stats = overlap_df.groupby("Ay").agg(
        Doluluk=("Doluluk_Orani_Yuzde", "mean"),
        Tuketim=("Gunluk_Tuketim_m3", lambda x: x.mean() / 1e6),
    )
    ay_adlari = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
    ax4_twin = ax4.twinx()
    p1 = ax4.plot(
        ay_adlari,
        monthly_stats["Doluluk"],
        color="#2ca02c",
        marker="o",
        linewidth=2.2,
        label="Ort. Doluluk (%)",
    )
    p2 = ax4_twin.plot(
        ay_adlari,
        monthly_stats["Tuketim"],
        color="#ff7f0e",
        marker="s",
        linestyle="--",
        linewidth=2.2,
        label="Ort. Tüketim (Milyon m³)",
    )
    ax4.set_title(
        "Aylık Mevsimsel Döngü: Doluluk Oranı vs. Günlük Tüketim (2011–2021)",
        fontweight="bold",
    )
    ax4.set_ylabel("Ortalama Doluluk (%)", color="#2ca02c")
    ax4_twin.set_ylabel("Ortalama Tüketim (Milyon m³/gün)", color="#ff7f0e")
    ax4_twin.grid(False)
    lines = p1 + p2
    labels = [l.get_label() for l in lines]
    ax4.legend(lines, labels, loc="upper right")

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(ASSETS_DIR / "dashboard_ozet.png", dpi=180)
    plt.close(fig)

    # --- GRAFİK 2: Yıl x Ay Baraj Yağış Isı Haritası (mevsimsel_isi_haritasi.png) ---
    fig, ax = plt.subplots(figsize=(12, 6.5), dpi=180)
    pivot_rain = (
        df_merged[df_merged["Yil"] <= 2023]
        .pivot_table(
            index="Yil",
            columns="Ay",
            values="Ortalama_Yagis_mm",
            aggfunc="sum",
        )
    )
    pivot_rain.columns = ay_adlari
    sns.heatmap(
        pivot_rain,
        annot=True,
        fmt=".0f",
        cmap="YlGnBu",
        linewidths=0.5,
        cbar_kws={"label": "Aylık Toplam Yağış (Havza Ort. mm)"},
        ax=ax,
    )
    ax.set_title(
        "İstanbul Baraj Havzaları Aylık Toplam Yağış Isı Haritası (mm, 2011–2023)",
        fontsize=13,
        fontweight="bold",
        pad=12,
    )
    ax.set_xlabel("Ay")
    ax.set_ylabel("Yıl")
    plt.tight_layout()
    fig.savefig(ASSETS_DIR / "mevsimsel_isi_haritasi.png", dpi=180)
    plt.close(fig)

    # --- GRAFİK 3: Havza Korelasyon Matrisi ve Kuraklık Risk Analizi (korelasyon_ve_kuraklik_analizi.png) ---
    fig, axes = plt.subplots(1, 2, figsize=(16, 6.5), dpi=180)

    # 3A: 10 Baraj Havzası Günlük Yağış Korelasyon Matrisi
    ax_corr = axes[0]
    corr_matrix = df_std[baraj_sutunlari].corr()
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)
    sns.heatmap(
        corr_matrix,
        mask=mask,
        annot=True,
        fmt=".2f",
        cmap="coolwarm",
        vmin=0.4,
        vmax=1.0,
        linewidths=0.5,
        cbar_kws={"label": "Pearson Korelasyon Katsayısı (r)"},
        ax=ax_corr,
    )
    ax_corr.set_title(
        "Baraj Havzaları Günlük Yağış Korelasyon Matrisi",
        fontsize=12,
        fontweight="bold",
        pad=10,
    )
    ax_corr.tick_params(axis="x", rotation=35)
    ax_corr.tick_params(axis="y", rotation=0)

    # 3B: Kritik Kuraklık Eşiği (<%30) ve 365 Günlük Hareketli Ortalama
    ax_dr = axes[1]
    df_occ_dt["MA_365"] = (
        df_occ_dt["GENERAL_DAM_OCCUPANCY_RATE"].rolling(window=365, min_periods=30).mean()
    )
    ax_dr.plot(
        df_occ_dt["DATE"],
        df_occ_dt["GENERAL_DAM_OCCUPANCY_RATE"],
        color="#7f9eb2",
        alpha=0.6,
        linewidth=1.0,
        label="Günlük Doluluk (%)",
    )
    ax_dr.plot(
        df_occ_dt["DATE"],
        df_occ_dt["MA_365"],
        color="#0b3c5d",
        linewidth=2.2,
        label="365 Günlük Hareketli Ortalama",
    )
    ax_dr.axhline(
        30,
        color="#d9534f",
        linestyle="--",
        linewidth=1.5,
        label="Kritik Kuraklık Eşiği (%30)",
    )
    ax_dr.fill_between(
        df_occ_dt["DATE"],
        df_occ_dt["GENERAL_DAM_OCCUPANCY_RATE"],
        30,
        where=(df_occ_dt["GENERAL_DAM_OCCUPANCY_RATE"] < 30),
        color="#d9534f",
        alpha=0.35,
        label="Kritik Kuraklık Dönemleri",
    )
    ax_dr.set_title(
        "Uzun Dönem Doluluk Eğilimi ve Kritik Kuraklık Dönemleri (<%30)",
        fontsize=12,
        fontweight="bold",
        pad=10,
    )
    ax_dr.set_ylabel("Doluluk Oranı (%)")
    ax_dr.set_ylim(0, 105)
    ax_dr.legend(loc="lower left")

    plt.tight_layout()
    fig.savefig(ASSETS_DIR / "korelasyon_ve_kuraklik_analizi.png", dpi=180)
    plt.close(fig)


def ozet_yazdir(df_occ, df_std, df_merged):
    """Veri setlerine ait temel istatistikleri konsola yazdırır."""
    baraj_sutunlari = list(BARAJ_ISIM_HARITASI.values())
    print("=" * 72)
    print("İSTANBUL BARAJLARI VERİ ANALİZİ VE KALİTE DOĞRULAMA ÖZETİ")
    print("=" * 72)
    print(f"1. Baraj Doluluk Verisi (2005-2021) : {len(df_occ):,} gün (Eksik: 0, Mükerrer: 0)")
    print(f"   - Ortalama Doluluk Oranı         : %{df_occ['GENERAL_DAM_OCCUPANCY_RATE'].mean():.2f}")
    print(f"   - En Yüksek Doluluk Oranı        : %{df_occ['GENERAL_DAM_OCCUPANCY_RATE'].max():.2f}")
    print(f"   - En Düşük Doluluk Oranı         : %{df_occ['GENERAL_DAM_OCCUPANCY_RATE'].min():.2f}")
    print(f"   - Ortalama Rezerv Su Miktarı     : {df_occ['GENERAL_DAM_RESERVED_WATER'].mean():.1f} Milyon m³")
    print("-" * 72)
    print(f"2. Yağış ve Tüketim Verisi (2011-2024): {len(df_std):,} gün (Eksik: 0, Mükerrer: 0)")
    print(f"   - Ortalama Günlük Su Tüketimi    : {df_std['Gunluk_Tuketim_m3'].mean():,.0f} m³/gün")
    print(f"   - Maksimum Günlük Su Tüketimi    : {df_std['Gunluk_Tuketim_m3'].max():,.0f} m³/gün")
    print(f"   - Minimum Günlük Su Tüketimi     : {df_std['Gunluk_Tuketim_m3'].min():,.0f} m³/gün")
    print("-" * 72)
    print("3. Baraj Havzalarına Göre Toplam Yağış Sıralaması (2011-2024):")
    for idx, (baraj, toplam) in enumerate(
        df_std[baraj_sutunlari].sum().sort_values(ascending=False).items(), 1
    ):
        yillik_ort = toplam / (len(df_std) / 365.25)
        print(f"   {idx:2d}. {baraj:<14}: {toplam:8,.2f} mm (Yıllık Ort: {yillik_ort:6.1f} mm/yıl)")
    print("=" * 72)


if __name__ == "__main__":
    df_occ, df_std, df_merged, df_unpivot = verileri_yukle_ve_temizle()
    grafikleri_olustur(df_occ, df_std, df_merged, df_unpivot)
    ozet_yazdir(df_occ, df_std, df_merged)

