# 📊 Power BI Veri Modeli, DAX ve Power Query (M) Rehberi

Bu doküman, `108_analiz.pbix` raporunu genişletmek veya sıfırdan yıldız şeması (**Star Schema**) kurmak isteyen analistler için hazır **DAX ölçülerini**, **Power Query (M)** dönüşüm kodlarını ve özel **Power BI Tema** kurulum adımlarını içerir.

---

## 🎨 1. Kurumsal Power BI Temasını Yükleme

Depodaki [`powerbi/istanbul_su_temasi.json`](istanbul_su_temasi.json) dosyası su kaynakları analizine uygun okyanus mavisi ve turkuaz renk paletini içerir:

1. **Power BI Desktop**'ta `108_analiz.pbix` dosyasını açın.
2. Üst menüden **Görünüm (View)** sekmesine geçin.
3. **Temalar (Themes)** açılır menüsünden **Temalara Göz At (Browse for themes)** seçeneğine tıklayın.
4. `powerbi/istanbul_su_temasi.json` dosyasını seçin.

---

## 📐 2. Dinamik Takvim Tablosu (`Dim_Tarih` - DAX)

`Fact_Istanbul_Baraj` (2011–2024) ve `Dim_Dam_Occupancy` (2005–2021) tablolarını ortak bir zaman boyutunda filtrelemek için **Modelleme -> Yeni Tablo** menüsünden aşağıdaki DAX tablosunu oluşturabilirsiniz:

```dax
Dim_Tarih = 
ADDCOLUMNS (
    CALENDAR ( DATE ( 2005, 1, 1 ), DATE ( 2024, 12, 31 ) ),
    "Yıl", YEAR ( [Date] ),
    "Çeyrek", "Ç" & FORMAT ( [Date], "Q" ),
    "Ay No", MONTH ( [Date] ),
    "Ay Adı", FORMAT ( [Date], "MMMM", "tr-TR" ),
    "Ay Kısa", FORMAT ( [Date], "MMM", "tr-TR" ),
    "Yıl-Ay", FORMAT ( [Date], "YYYY-MM" ),
    "Hafta Günü", FORMAT ( [Date], "dddd", "tr-TR" ),
    "Hafta Sonu Mu", IF ( WEEKDAY ( [Date], 2 ) >= 6, "Hafta Sonu", "Hafta İçi" ),
    "Mevsim",
        SWITCH (
            TRUE (),
            MONTH ( [Date] ) IN { 12, 1, 2 }, "Kış",
            MONTH ( [Date] ) IN { 3, 4, 5 }, "İlkbahar",
            MONTH ( [Date] ) IN { 6, 7, 8 }, "Yaz",
            "Sonbahar"
        )
)
```

---

## 🧮 3. İleri Seviye DAX Ölçüleri (Measures)

```dax
// --- TEMEL KART ÖLÇÜLERİ ---

Ortalama Doluluk Oranı (%) = 
AVERAGE ( Dim_Dam_Occupancy[GENERAL_DAM_OCCUPANCY_RATE] )

Ortalama Rezerv Su (Milyon m³) = 
AVERAGE ( Dim_Dam_Occupancy[GENERAL_DAM_RESERVED_WATER] )

Ortalama Günlük Tüketim (m³) = 
AVERAGE ( Fact_Istanbul_Baraj[İstanbul günlük tüketim(m³/gün)] )

Toplam Su Tüketimi (Milyon m³) = 
DIVIDE ( SUM ( Fact_Istanbul_Baraj[İstanbul günlük tüketim(m³/gün)] ), 1000000, 0 )


// --- HAREKETLİ ORTALAMA VE TREND ÖLÇÜLERİ ---

30 Günlük Hareketli Ort. Doluluk (%) = 
AVERAGEX (
    DATESINPERIOD (
        Dim_Dam_Occupancy[DATE],
        LASTDATE ( Dim_Dam_Occupancy[DATE] ),
        -30,
        DAY
    ),
    [Ortalama Doluluk Oranı (%)]
)

30 Günlük Hareketli Ort. Tüketim (m³) = 
AVERAGEX (
    DATESINPERIOD (
        Fact_Istanbul_Baraj[Tarih],
        LASTDATE ( Fact_Istanbul_Baraj[Tarih] ),
        -30,
        DAY
    ),
    [Ortalama Günlük Tüketim (m³)]
)


// --- YILLIK DEĞİŞİM (YoY) VE KURAKLIK RİSK DURUMU ---

Tüketim YoY Değişim (%) = 
VAR MevcutDeger = [Ortalama Günlük Tüketim (m³)]
VAR GecenYilDeger = 
    CALCULATE (
        [Ortalama Günlük Tüketim (m³)],
        SAMEPERIODLASTYEAR ( Fact_Istanbul_Baraj[Tarih] )
    )
RETURN
    DIVIDE ( MevcutDeger - GecenYilDeger, GecenYilDeger, 0 )

Kuraklık Risk Seviyesi = 
VAR Doluluk = [Ortalama Doluluk Oranı (%)]
RETURN
    SWITCH (
        TRUE (),
        ISBLANK ( Doluluk ), "Veri Yok",
        Doluluk < 30, "🔴 Kritik Risk (<%30)",
        Doluluk < 50, "🟠 Orta Risk (%30-%50)",
        Doluluk < 75, "🟢 Normal Seviye (%50-%75)",
        "🔵 Yüksek Doluluk (>%75)"
    )
```

---

## 🔄 4. Power Query (M) Unpivot Dönüşüm Kodu

Excel tablosundaki 10 baraj sütununu Power Query içinde dinamik olarak **Unpivot (Uzun Format)** haline getirmek için Gelişmiş Düzenleyici'de (Advanced Editor) şu adımı kullanabilirsiniz:

```powerquery
let
    Kaynak = Excel.Workbook(File.Contents("istanbul-barajlarnda-ya-ve-gunluk-tuketim-verileri.xlsx"), null, true),
    Sayfa1_Sheet = Kaynak{[Item="Sayfa1",Kind="Sheet"]}[Data],
    TanitilanBasliklar = Table.PromoteHeaders(Sayfa1_Sheet, [PromoteAllScalars=true]),
    TemizSutunAdlari = Table.RenameColumns(TanitilanBasliklar, {
        {"Darlik", "Darlık"},
        {"Elmali", "Elmalı"},
        {"B.çekmece", "Büyükçekmece"},
        {"Sazlidere", "Sazlıdere"},
        {"ıstırancalar", "Istrancalar"}
    }),
    UnpivotBarajlar = Table.UnpivotOtherColumns(
        TemizSutunAdlari,
        {"Tarih", "İstanbul günlük tüketim(m³/gün)"},
        "Baraj_Adi",
        "Yagis_mm"
    ),
    VeriTipleri = Table.TransformColumnTypes(UnpivotBarajlar, {
        {"Tarih", type date},
        {"Baraj_Adi", type text},
        {"Yagis_mm", type number},
        {"İstanbul günlük tüketim(m³/gün)", Int64.Type}
    })
in
    VeriTipleri
```
