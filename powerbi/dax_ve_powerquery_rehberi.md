# 📊 Power BI Data Model, DAX Measures & Power Query (M) Guide

This guide provides ready-to-use **DAX formulas**, a dynamic **Calendar dimension table (`Dim_Tarih`)**, **Power Query (M)** unpivoting scripts, and instructions for applying the custom **Power BI JSON Theme** to `108_analiz.pbix`.

---

## 🎨 1. Applying the Custom Power BI Theme

The [`powerbi/istanbul_su_temasi.json`](istanbul_su_temasi.json) file defines an ocean-blue and teal corporate color palette tailored for hydrological and utility analytics:

1. Open `108_analiz.pbix` in **Power BI Desktop**.
2. Navigate to the **View** tab in the top ribbon.
3. Click the **Themes** dropdown and select **Browse for themes**.
4. Select `powerbi/istanbul_su_temasi.json`.

---

## 📐 2. Dynamic Calendar Table (`Dim_Tarih` - DAX)

To filter both `Fact_Istanbul_Baraj` (`2011–2024`) and `Dim_Dam_Occupancy` (`2005–2021`) across a unified date dimension, create a calculated table via **Modeling -> New Table**:

```dax
Dim_Tarih = 
ADDCOLUMNS (
    CALENDAR ( DATE ( 2005, 1, 1 ), DATE ( 2024, 12, 31 ) ),
    "Year", YEAR ( [Date] ),
    "Quarter", "Q" & FORMAT ( [Date], "Q" ),
    "Month Number", MONTH ( [Date] ),
    "Month Name", FORMAT ( [Date], "MMMM", "en-US" ),
    "Month Short", FORMAT ( [Date], "MMM", "en-US" ),
    "Year-Month", FORMAT ( [Date], "YYYY-MM" ),
    "Day of Week", FORMAT ( [Date], "dddd", "en-US" ),
    "Is Weekend", IF ( WEEKDAY ( [Date], 2 ) >= 6, "Weekend", "Weekday" ),
    "Season",
        SWITCH (
            TRUE (),
            MONTH ( [Date] ) IN { 12, 1, 2 }, "Winter",
            MONTH ( [Date] ) IN { 3, 4, 5 }, "Spring",
            MONTH ( [Date] ) IN { 6, 7, 8 }, "Summer",
            "Autumn"
        )
)
```

---

## 🧮 3. Advanced DAX Measures

```dax
// --- CORE KPI MEASURES ---

Average Occupancy Rate (%) = 
AVERAGE ( Dim_Dam_Occupancy[GENERAL_DAM_OCCUPANCY_RATE] )

Average Reserved Water (Million m³) = 
AVERAGE ( Dim_Dam_Occupancy[GENERAL_DAM_RESERVED_WATER] )

Average Daily Consumption (m³) = 
AVERAGE ( Fact_Istanbul_Baraj[İstanbul günlük tüketim(m³/gün)] )

Total Water Consumption (Million m³) = 
DIVIDE ( SUM ( Fact_Istanbul_Baraj[İstanbul günlük tüketim(m³/gün)] ), 1000000, 0 )


// --- ROLLING AVERAGES & SMOOTHED TRENDS ---

30-Day Moving Avg Occupancy (%) = 
AVERAGEX (
    DATESINPERIOD (
        Dim_Dam_Occupancy[DATE],
        LASTDATE ( Dim_Dam_Occupancy[DATE] ),
        -30,
        DAY
    ),
    [Average Occupancy Rate (%)]
)

30-Day Moving Avg Consumption (m³) = 
AVERAGEX (
    DATESINPERIOD (
        Fact_Istanbul_Baraj[Tarih],
        LASTDATE ( Fact_Istanbul_Baraj[Tarih] ),
        -30,
        DAY
    ),
    [Average Daily Consumption (m³)]
)


// --- YEAR-OVER-YEAR (YoY) GROWTH & DROUGHT RISK TIER ---

Consumption YoY Growth (%) = 
VAR CurrentValue = [Average Daily Consumption (m³)]
VAR PriorYearValue = 
    CALCULATE (
        [Average Daily Consumption (m³)],
        SAMEPERIODLASTYEAR ( Fact_Istanbul_Baraj[Tarih] )
    )
RETURN
    DIVIDE ( CurrentValue - PriorYearValue, PriorYearValue, 0 )

Drought Risk Tier = 
VAR Occupancy = [Average Occupancy Rate (%)]
RETURN
    SWITCH (
        TRUE (),
        ISBLANK ( Occupancy ), "No Data",
        Occupancy < 30, "🔴 Critical Risk (<30%)",
        Occupancy < 50, "🟠 Moderate Risk (30%-50%)",
        Occupancy < 75, "🟢 Normal Level (50%-75%)",
        "🔵 High Capacity (>75%)"
    )
```

---

## 🔄 4. Power Query (M) Dynamic Unpivot Script

To dynamically unpivot the 10 dam columns inside Power Query (**Home -> Transform Data -> Advanced Editor**):

```powerquery
let
    Source = Excel.Workbook(File.Contents("istanbul-barajlarnda-ya-ve-gunluk-tuketim-verileri.xlsx"), null, true),
    Sayfa1_Sheet = Source{[Item="Sayfa1",Kind="Sheet"]}[Data],
    PromotedHeaders = Table.PromoteHeaders(Sayfa1_Sheet, [PromoteAllScalars=true]),
    StandardizedColumns = Table.RenameColumns(PromotedHeaders, {
        {"Darlik", "Darlık"},
        {"Elmali", "Elmalı"},
        {"B.çekmece", "Büyükçekmece"},
        {"Sazlidere", "Sazlıdere"},
        {"ıstırancalar", "Istrancalar"}
    }),
    UnpivotedDams = Table.UnpivotOtherColumns(
        StandardizedColumns,
        {"Tarih", "İstanbul günlük tüketim(m³/gün)"},
        "Baraj_Adi",
        "Yagis_mm"
    ),
    TypedColumns = Table.TransformColumnTypes(UnpivotedDams, {
        {"Tarih", type date},
        {"Baraj_Adi", type text},
        {"Yagis_mm", type number},
        {"İstanbul günlük tüketim(m³/gün)", Int64.Type}
    })
in
    TypedColumns
```
