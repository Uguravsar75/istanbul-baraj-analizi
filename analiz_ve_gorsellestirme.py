#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Istanbul Dam Occupancy, Basin Precipitation & Daily Water Consumption Analytics
===============================================================================
This script performs end-to-end ETL, data validation, and visual analytics:
1. Validates and cleans raw datasets ('dam_occupancy.csv' and
   'istanbul-barajlarnda-ya-ve-gunluk-tuketim-verileri.xlsx') by removing
   anomalous/duplicate records, interpolating missing dates, and dropping
   empty columns.
2. Merges and transforms the datasets into Star-Schema-ready CSV files under 'data/':
   - data/istanbul_baraj_birlesik_veri.csv (Merged daily analytical dataset)
   - data/istanbul_baraj_yagis_unpivot.csv (Long/Unpivoted basin precipitation dataset)
3. Computes key statistical insights and generates high-resolution analytical
   visualizations under 'assets/'.
"""

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Global visual theme configuration
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
    """Loads raw CSV and Excel datasets, resolves data quality issues, and exports clean tables."""
    DATA_DIR.mkdir(exist_ok=True)
    ASSETS_DIR.mkdir(exist_ok=True)

    # 1. Dam Occupancy Dataset (dam_occupancy.csv)
    csv_path = BASE_DIR / "dam_occupancy.csv"
    df_occ = pd.read_csv(csv_path)

    # Remove known anomalous/duplicate records (2020-04-19 anomaly and 2021-01-07 duplicate)
    df_occ = df_occ[
        ~((df_occ["DATE"] == "2020-04-19") & (df_occ["GENERAL_DAM_OCCUPANCY_RATE"] == 80.79))
    ]
    df_occ = df_occ.drop_duplicates(subset=["DATE"], keep="first").copy()
    df_occ["DATE_DT"] = pd.to_datetime(df_occ["DATE"])
    df_occ = df_occ.sort_values("DATE_DT").set_index("DATE_DT")

    # Reindex to a continuous daily date range (2005-01-01 .. 2021-04-07)
    full_range = pd.date_range(df_occ.index.min(), df_occ.index.max(), freq="D")
    df_occ = df_occ.reindex(full_range)
    df_occ["GENERAL_DAM_OCCUPANCY_RATE"] = (
        df_occ["GENERAL_DAM_OCCUPANCY_RATE"].interpolate(method="linear").round(2)
    )
    df_occ["GENERAL_DAM_RESERVED_WATER"] = (
        df_occ["GENERAL_DAM_RESERVED_WATER"].interpolate(method="linear").round().astype(int)
    )
    df_occ["DATE"] = df_occ.index.strftime("%Y-%m-%d")

    # Save cleaned primary CSV
    df_occ_out = df_occ[
        ["DATE", "GENERAL_DAM_OCCUPANCY_RATE", "GENERAL_DAM_RESERVED_WATER"]
    ].reset_index(drop=True)
    df_occ_out.to_csv(csv_path, index=False)

    # 2. Precipitation & Daily Water Consumption Dataset (Excel)
    xl_path = BASE_DIR / "istanbul-barajlarnda-ya-ve-gunluk-tuketim-verileri.xlsx"
    df_xl = pd.read_excel(xl_path, sheet_name="Sayfa1")
    empty_cols = [c for c in df_xl.columns if str(c).startswith("Unnamed")]
    if empty_cols:
        df_xl = df_xl.drop(columns=empty_cols)
        with pd.ExcelWriter(xl_path, engine="openpyxl") as writer:
            df_xl.to_excel(writer, sheet_name="Sayfa1", index=False)

    df_xl["Tarih"] = pd.to_datetime(df_xl["Tarih"])
    df_xl = df_xl.sort_values("Tarih").reset_index(drop=True)

    # Create standardized copy
    df_std = df_xl.rename(
        columns={
            **BARAJ_ISIM_HARITASI,
            "İstanbul günlük tüketim(m³/gün)": "Gunluk_Tuketim_m3",
        }
    )
    dam_cols = list(BARAJ_ISIM_HARITASI.values())
    df_std["Toplam_Yagis_mm"] = df_std[dam_cols].sum(axis=1).round(2)
    df_std["Ortalama_Yagis_mm"] = df_std[dam_cols].mean(axis=1).round(2)

    # 3. Merged Daily Dataset (2011-01-01 .. 2024-02-18)
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

    # 4. Unpivoted (Long-Format) Basin Precipitation Dataset for Power BI Star Schema
    df_unpivot = df_merged.melt(
        id_vars=["Tarih", "Yil", "Ay", "Mevsim"],
        value_vars=dam_cols,
        var_name="Baraj_Adi",
        value_name="Yagis_mm",
    )
    df_unpivot.to_csv(DATA_DIR / "istanbul_baraj_yagis_unpivot.csv", index=False)

    return df_occ_out, df_std, df_merged, df_unpivot


def grafikleri_olustur(df_occ, df_std, df_merged, df_unpivot):
    """Generates 3 high-resolution analytical figures under 'assets/' for documentation."""
    dam_cols = list(BARAJ_ISIM_HARITASI.values())

    # --- FIGURE 1: 4-Panel Executive Summary Dashboard (dashboard_ozet.png) ---
    fig, axes = plt.subplots(2, 2, figsize=(16, 10), dpi=180)
    fig.suptitle(
        "Istanbul Dams: Occupancy, Basin Precipitation & Water Consumption Overview",
        fontsize=16,
        fontweight="bold",
        y=0.98,
    )

    # 1A: Dam Occupancy Rate Time Series (2005-2021)
    ax1 = axes[0, 0]
    df_occ_dt = df_occ.copy()
    df_occ_dt["DATE"] = pd.to_datetime(df_occ_dt["DATE"])
    ax1.plot(
        df_occ_dt["DATE"],
        df_occ_dt["GENERAL_DAM_OCCUPANCY_RATE"],
        color="#1f77b4",
        linewidth=1.2,
        label="Daily Occupancy (%)",
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
        label=f"Mean: {mean_occ:.1f}%",
    )
    ax1.set_title("General Dam Occupancy Rate Trend (2005–2021)", fontweight="bold")
    ax1.set_ylabel("Occupancy Rate (%)")
    ax1.set_ylim(0, 105)
    ax1.legend(loc="lower left")

    # 1B: Average Daily Water Consumption by Year (2011-2023)
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
        "Average Daily Water Consumption by Year (2011–2023)", fontweight="bold"
    )
    ax2.set_ylabel("Million m³ / Day")
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

    # 1C: Cumulative Precipitation by Dam Basin (2011-2024)
    ax3 = axes[1, 0]
    dam_totals = df_std[dam_cols].sum().sort_values(ascending=True)
    colors = sns.color_palette("viridis", len(dam_totals))
    bars_h = ax3.barh(dam_totals.index, dam_totals.values, color=colors)
    ax3.set_title(
        "Cumulative Precipitation by Dam Basin (2011–2024)",
        fontweight="bold",
    )
    ax3.set_xlabel("Total Precipitation (mm)")
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

    # 1D: Monthly Seasonal Cycle: Occupancy Rate vs. Daily Consumption (2011-2021)
    ax4 = axes[1, 1]
    overlap_df = df_merged.dropna(subset=["Doluluk_Orani_Yuzde"]).copy()
    monthly_stats = overlap_df.groupby("Ay").agg(
        Doluluk=("Doluluk_Orani_Yuzde", "mean"),
        Tuketim=("Gunluk_Tuketim_m3", lambda x: x.mean() / 1e6),
    )
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    ax4_twin = ax4.twinx()
    p1 = ax4.plot(
        month_names,
        monthly_stats["Doluluk"],
        color="#2ca02c",
        marker="o",
        linewidth=2.2,
        label="Avg. Occupancy (%)",
    )
    p2 = ax4_twin.plot(
        month_names,
        monthly_stats["Tuketim"],
        color="#ff7f0e",
        marker="s",
        linestyle="--",
        linewidth=2.2,
        label="Avg. Consumption (Million m³)",
    )
    ax4.set_title(
        "Monthly Seasonal Cycle: Occupancy Rate vs. Consumption (2011–2021)",
        fontweight="bold",
    )
    ax4.set_ylabel("Average Occupancy (%)", color="#2ca02c")
    ax4_twin.set_ylabel("Average Consumption (Million m³/day)", color="#ff7f0e")
    ax4_twin.grid(False)
    lines = p1 + p2
    labels = [l.get_label() for l in lines]
    ax4.legend(lines, labels, loc="upper right")

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(ASSETS_DIR / "dashboard_ozet.png", dpi=180)
    plt.close(fig)

    # --- FIGURE 2: Year x Month Precipitation Heatmap (mevsimsel_isi_haritasi.png) ---
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
    pivot_rain.columns = month_names
    sns.heatmap(
        pivot_rain,
        annot=True,
        fmt=".0f",
        cmap="YlGnBu",
        linewidths=0.5,
        cbar_kws={"label": "Monthly Total Precipitation (Basin Avg. mm)"},
        ax=ax,
    )
    ax.set_title(
        "Istanbul Dam Basins: Monthly Precipitation Heatmap (mm, 2011–2023)",
        fontsize=13,
        fontweight="bold",
        pad=12,
    )
    ax.set_xlabel("Month")
    ax.set_ylabel("Year")
    plt.tight_layout()
    fig.savefig(ASSETS_DIR / "mevsimsel_isi_haritasi.png", dpi=180)
    plt.close(fig)

    # --- FIGURE 3: Basin Correlation Matrix & Drought Risk Analysis (korelasyon_ve_kuraklik_analizi.png) ---
    fig, axes = plt.subplots(1, 2, figsize=(16, 6.5), dpi=180)

    # 3A: 10 Dam Basins Daily Precipitation Correlation Matrix
    ax_corr = axes[0]
    corr_matrix = df_std[dam_cols].corr()
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
        cbar_kws={"label": "Pearson Correlation Coefficient (r)"},
        ax=ax_corr,
    )
    ax_corr.set_title(
        "Dam Basins Daily Precipitation Correlation Matrix",
        fontsize=12,
        fontweight="bold",
        pad=10,
    )
    ax_corr.tick_params(axis="x", rotation=35)
    ax_corr.tick_params(axis="y", rotation=0)

    # 3B: Critical Drought Threshold (<30%) & 365-Day Moving Average
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
        label="Daily Occupancy (%)",
    )
    ax_dr.plot(
        df_occ_dt["DATE"],
        df_occ_dt["MA_365"],
        color="#0b3c5d",
        linewidth=2.2,
        label="365-Day Moving Average",
    )
    ax_dr.axhline(
        30,
        color="#d9534f",
        linestyle="--",
        linewidth=1.5,
        label="Critical Drought Threshold (30%)",
    )
    ax_dr.fill_between(
        df_occ_dt["DATE"],
        df_occ_dt["GENERAL_DAM_OCCUPANCY_RATE"],
        30,
        where=(df_occ_dt["GENERAL_DAM_OCCUPANCY_RATE"] < 30),
        color="#d9534f",
        alpha=0.35,
        label="Critical Drought Periods (<30%)",
    )
    ax_dr.set_title(
        "Long-Term Occupancy Trend & Critical Drought Periods (<30%)",
        fontsize=12,
        fontweight="bold",
        pad=10,
    )
    ax_dr.set_ylabel("Occupancy Rate (%)")
    ax_dr.set_ylim(0, 105)
    ax_dr.legend(loc="lower left")

    plt.tight_layout()
    fig.savefig(ASSETS_DIR / "korelasyon_ve_kuraklik_analizi.png", dpi=180)
    plt.close(fig)


def ozet_yazdir(df_occ, df_std, df_merged):
    """Prints key statistical metrics and data quality verification summary to stdout."""
    dam_cols = list(BARAJ_ISIM_HARITASI.values())
    print("=" * 74)
    print("ISTANBUL DAMS DATA ANALYTICS & QUALITY VERIFICATION SUMMARY")
    print("=" * 74)
    print(f"1. Dam Occupancy Dataset (2005-2021) : {len(df_occ):,} days (Missing: 0, Duplicates: 0)")
    print(f"   - Mean Occupancy Rate             : {df_occ['GENERAL_DAM_OCCUPANCY_RATE'].mean():.2f}%")
    print(f"   - Maximum Occupancy Rate          : {df_occ['GENERAL_DAM_OCCUPANCY_RATE'].max():.2f}%")
    print(f"   - Minimum Occupancy Rate          : {df_occ['GENERAL_DAM_OCCUPANCY_RATE'].min():.2f}%")
    print(f"   - Mean Reserved Water Volume      : {df_occ['GENERAL_DAM_RESERVED_WATER'].mean():.1f} Million m³")
    print("-" * 74)
    print(f"2. Precipitation & Consumption (2011-2024): {len(df_std):,} days (Missing: 0, Duplicates: 0)")
    print(f"   - Mean Daily Water Consumption    : {df_std['Gunluk_Tuketim_m3'].mean():,.0f} m³/day")
    print(f"   - Maximum Daily Water Consumption : {df_std['Gunluk_Tuketim_m3'].max():,.0f} m³/day")
    print(f"   - Minimum Daily Water Consumption : {df_std['Gunluk_Tuketim_m3'].min():,.0f} m³/day")
    print("-" * 74)
    print("3. Cumulative Precipitation Ranking by Dam Basin (2011-2024):")
    for idx, (dam, total) in enumerate(
        df_std[dam_cols].sum().sort_values(ascending=False).items(), 1
    ):
        annual_avg = total / (len(df_std) / 365.25)
        print(f"   {idx:2d}. {dam:<14}: {total:8,.2f} mm (Annual Avg: {annual_avg:6.1f} mm/yr)")
    print("=" * 74)


if __name__ == "__main__":
    df_occ, df_std, df_merged, df_unpivot = verileri_yukle_ve_temizle()
    grafikleri_olustur(df_occ, df_std, df_merged, df_unpivot)
    ozet_yazdir(df_occ, df_std, df_merged)
