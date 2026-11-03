# 💧 İstanbul Barajları Doluluk, Yağış ve Günlük Su Tüketimi Analizi

Bu proje, İstanbul'daki **10 ana baraj havzasının** (Ömerli, Darlık, Elmalı, Terkos, Büyükçekmece, Sazlıdere, Alibey, Kazandere, Pabuçdere, Istrancalar) günlük yağış verilerini, İstanbul genel baraj doluluk oranlarını, rezerv su miktarlarını ve günlük su tüketim eğilimlerini **Power BI** ve **Python** kullanarak inceleyen kapsamlı bir veri analitiği çalışmasıdır.

![İstanbul Barajları Analiz Paneli](assets/dashboard_ozet.png)

---

## 🎯 Projenin Amacı

- **İklim ve Kuraklık Takibi:** 2005–2021 yılları arasındaki günlük baraj doluluk oranlarını ve 2011–2024 yılları arasındaki baraj havzası yağışlarını inceleyerek kurak dönemleri tespit etmek.
- **Tüketim Trendi Analizi:** İstanbul'un nüfus ve kullanım artışına paralel olarak günlük su tüketiminin yıllar ve mevsimler bazında nasıl değiştiğini ortaya koymak.
- **Mevsimsel Döngü Modellemesi:** Barajların en yüksek doluluğa ulaştığı ilkbahar ayları ile su tüketiminin zirve yaptığı yaz ayları arasındaki ters yönlü mevsimsel ilişkiyi görselleştirmek.
- **İş Zekası (BI) Raporlaması:** Power BI (`108_analiz.pbix`) üzerinde interaktif filtreleme, zaman hiyerarşisi ve baraj bazlı karşılaştırma imkânı sunan bir gösterge paneli oluşturmak.

---

## 📂 Veri Setleri ve Veri Kalitesi İyileştirmeleri (ETL)

Projede iki temel veri kaynağı kullanılmış, ham verilerdeki kalite sorunları giderilerek analize hazır türetilmiş tablolar üretilmiştir:

| Dosya Adı | Kapsam / Dönem | Satır Sayısı | Açıklama |
| :--- | :--- | :---: | :--- |
| `dam_occupancy.csv` | `2005-01-01` – `2021-04-07` | 5.941 gün | Günlük genel baraj doluluk oranı (`%`) ve rezerv su hacmi (`Milyon m³`). |
| `istanbul-barajlarnda-ya-ve-gunluk-tuketim-verileri.xlsx` | `2011-01-01` – `2024-02-18` | 4.797 gün | 10 baraj havzasının günlük yağış miktarları (`mm`) ve İstanbul günlük su tüketimi (`m³/gün`). |
| `data/istanbul_baraj_birlesik_veri.csv` | `2011-01-01` – `2024-02-18` | 4.797 gün | Standartlaştırılmış sütun adları, toplam/ortalama yağış, mevsim ve doluluk verilerini içeren birleştirilmiş tablo. |
| `data/istanbul_baraj_yagis_unpivot.csv` | `2011-01-01` – `2024-02-18` | 47.970 satır | Power BI'da baraj bazlı dilimleme ve X-ekseni kullanımı için **Unpivot (Uzun Format)** haline getirilmiş yağış tablosu. |

### 🛠️ Yapılan Veri Temizleme (Data Cleaning) İşlemleri
1. **Mükerrer ve Hatalı Kayıtların Giderilmesi (`dam_occupancy.csv`):**
   - `2020-04-19` tarihinde yer alan hatalı/anomali kayıt (`%80.79 / 701 Milyon m³` — önceki ve sonraki gün `%70.08` ve `%70.01` iken) temizlendi, doğru kayıt (`%70.03 / 608 Milyon m³`) korundu.
   - `2021-01-07` tarihindeki birebir mükerrer satır kaldırılarak `DATE` sütununun Power BI `1:N` (One-to-Many) ilişkisi için **%100 tekil birincil anahtar (Primary Key)** olması sağlandı.
2. **Eksik Günlerin Tamamlanması (`dam_occupancy.csv`):**
   - Zaman serisinde eksik olan `2020-06-05` (`%66.50 / 578 Milyon m³`) ve `2020-07-31` (`%57.24 / 497 Milyon m³`) tarihleri komşu günlerle doğrusal interpolasyon (linear interpolation) uygulanarak tamamlandı.
3. **Yapısal Temizlik ve Standartlaştırma (`Excel`):**
   - Excel dosyasındaki tamamen boş `Unnamed: 11` (L sütunu) kaldırıldı.
   - Türkçe karakter ve büyük/küçük harf tutarsızlıkları (`ıstırancalar` $\rightarrow$ `Istrancalar`, `Darlik` $\rightarrow$ `Darlık`, `Elmali` $\rightarrow$ `Elmalı`, `Sazlidere` $\rightarrow$ `Sazlıdere`, `B.çekmece` $\rightarrow$ `Büyükçekmece`) standartlaştırıldı.

---

## 📊 Temel Analitik Bulgular

### 1. Baraj Doluluk Oranları (2005–2021)
- **Ortalama Doluluk Oranı:** `%64.76` (Ortalama Rezerv Su: `562.5 Milyon m³`)
- **En Yüksek Doluluk:** `%99.16` (`861 Milyon m³` — Nisan 2006 & Nisan 2010)
- **En Düşük Doluluk (Kritik Kuraklık):** `%9.20` (`80 Milyon m³` — Kasım 2007). Ayrıca **2014** (`%14.6`) ve **Ocak 2021** (`%19.16`) dönemleri yakın tarihin en sert kuraklık süreçleri olarak öne çıkmaktadır.

### 2. Günlük Su Tüketimi Eğilimi (2011–2024)
- **Ortalama Günlük Tüketim:** `2.737.182 m³/gün`
- **Minimum Tüketim:** `1.949.139 m³/gün` (`31 Mart 2015` — Türkiye genel elektrik kesintisi günü)
- **Maksimum Tüketim:** `3.568.056 m³/gün` (`2023 yaz dönemi`)
- **Yıllık Artış:** 2011 yılında ortalama `2.26 Milyon m³/gün` olan su tüketimi, 2023 yılına gelindiğinde **%35.4 artışla** ortalama `3.06 Milyon m³/gün` seviyesine ulaşmıştır.

### 3. Baraj Havzalarına Göre Yağış Dağılımı (2011–2024)
Kuzey ve Karadeniz kıyı kuşağındaki havzalar (Kazandere, Pabuçdere, Istrancalar, Terkos) en yüksek yağışı alırken, güneybatıdaki sığ havzalar (Büyükçekmece, Sazlıdere) en düşük yağışı almaktadır:

| Sıra | Baraj Havzası | Kümülatif Yağış (2011–2024) | Yıllık Ortalama Yağış | Günlük Maksimum Yağış |
| :---: | :--- | :---: | :---: | :---: |
| 1 | **Kazandere** | `12.469,71 mm` | `949,5 mm/yıl` | `170,20 mm` |
| 2 | **Pabuçdere** | `11.746,52 mm` | `894,4 mm/yıl` | `171,08 mm` |
| 3 | **Istrancalar** | `11.646,06 mm` | `886,7 mm/yıl` | `172,00 mm` |
| 4 | **Terkos** | `11.563,70 mm` | `880,5 mm/yıl` | `131,28 mm` |
| 5 | **Darlık** | `10.883,03 mm` | `828,6 mm/yıl` | `82,69 mm` |
| 6 | **Ömerli** | `9.952,14 mm` | `757,8 mm/yıl` | `123,53 mm` |
| 7 | **Alibey** | `9.682,35 mm` | `737,2 mm/yıl` | `119,00 mm` |
| 8 | **Elmalı** | `9.045,56 mm` | `688,7 mm/yıl` | `95,47 mm` |
| 9 | **Sazlıdere** | `8.734,18 mm` | `665,0 mm/yıl` | `178,25 mm` |
| 10 | **Büyükçekmece** | `8.057,23 mm` | `613,5 mm/yıl` | `95,59 mm` |

![Aylık Yağış Isı Haritası](assets/mevsimsel_isi_haritasi.png)

---

## 📈 Power BI Raporu (`108_analiz.pbix`)

Power BI raporu (`İstanbul Baraj ve Su Tüketim Analizi` sayfası) `1280x720` (16:9) standart tuval üzerinde 5 ana bileşenden oluşacak şekilde optimize edilmiştir:

1. **Ortalama Baraj Doluluk Oranı (%) Kartı:** Seçili dönemdeki ortalama baraj doluluk yüzdesini gösterir (`Average`).
2. **Toplam Su Tüketimi (m³) Kartı:** Seçili dönemdeki kümülatif su tüketimini gösterir (`Sum`).
3. **Tarih Aralığı Filtresi (Slicer):** `Between` (Tarih Aralığı Kaydırıcısı) modunda tüm raporu dinamik olarak filtreler.
4. **Yıllara Göre Baraj Havzaları Yağış Trendi (mm) Çizgi Grafiği:** Yıl $\rightarrow$ Çeyrek $\rightarrow$ Ay $\rightarrow$ Gün hiyerarşisinde (Drill-down destekli) 10 baraj havzasının yağış değişimini karşılaştırır.
5. **Baraj Havzalarına Göre Toplam Yağış Karşılaştırması (mm) Sütun Grafiği:** 10 baraj havzasının toplam yağış miktarlarını yan yana kıyaslar.

### 💡 Önerilen DAX Ölçüleri (Measures)
Raporu genişletirken kullanabileceğiniz temel DAX formülleri:

```dax
// 1. Ortalama Baraj Doluluk Oranı (%)
Ort_Doluluk_Orani = 
AVERAGE(Dim_Dam_Occupancy[GENERAL_DAM_OCCUPANCY_RATE])

// 2. Ortalama Günlük Su Tüketimi (m³/gün)
Ort_Gunluk_Tuketim_m3 = 
AVERAGE(Fact_Istanbul_Baraj[İstanbul günlük tüketim(m³/gün)])

// 3. Toplam Su Tüketimi (Milyon m³)
Toplam_Tuketim_Milyon_m3 = 
DIVIDE(SUM(Fact_Istanbul_Baraj[İstanbul günlük tüketim(m³/gün)]), 1000000, 0)

// 4. Geçen Yılın Aynı Dönemine Göre Tüketim Değişimi (YoY %)
Tuketim_YoY_Degisim = 
VAR MevcutTuketim = [Ort_Gunluk_Tuketim_m3]
VAR GecenYilTuketim = CALCULATE([Ort_Gunluk_Tuketim_m3], SAMEPERIODLASTYEAR(Fact_Istanbul_Baraj[Tarih]))
RETURN
DIVIDE(MevcutTuketim - GecenYilTuketim, GecenYilTuketim, 0)
```

---

## 🚀 Kurulum ve Çalıştırma

### 1. Python Analiz ve Görselleştirme Betiğini Çalıştırma
Veri temizleme, birleştirme ve grafik üretimi işlemlerini yeniden çalıştırmak için:

```bash
pip install -r requirements.txt
python3 analiz_ve_gorsellestirme.py
```

### 2. Power BI Raporunu Açma
- Bilgisayarınızda **Microsoft Power BI Desktop** yüklü olmalıdır.
- `108_analiz.pbix` dosyasına çift tıklayarak raporu doğrudan açabilirsiniz.
- Daha ileri seviye baraj kırılımı (X-ekseninde baraj adları ve dilimleyici) için `data/istanbul_baraj_yagis_unpivot.csv` ve `data/istanbul_baraj_birlesik_veri.csv` tablolarını veri modeline dahil edebilirsiniz.

---

## 📁 Proje Dizin Yapısı

```text
108_analiz/
├── 108_analiz.pbix                                           # Optimize edilmiş Power BI Raporu
├── dam_occupancy.csv                                         # Temizlenmiş günlük baraj doluluk verisi (2005-2021)
├── istanbul-barajlarnda-ya-ve-gunluk-tuketim-verileri.xlsx   # Temizlenmiş yağış ve günlük tüketim verisi (2011-2024)
├── analiz_ve_gorsellestirme.py                               # Veri doğrulama, temizleme, ETL ve görselleştirme betiği
├── data/
│   ├── istanbul_baraj_birlesik_veri.csv                      # Birleştirilmiş ve standartlaştırılmış günlük veri seti
│   └── istanbul_baraj_yagis_unpivot.csv                      # Baraj bazlı uzun format (Unpivot) yağış veri seti
├── assets/
│   ├── dashboard_ozet.png                                    # 4'lü yönetici özeti gösterge paneli görseli
│   └── mevsimsel_isi_haritasi.png                            # Yıl x Ay yağış ısı haritası (Heatmap)
├── requirements.txt                                          # Python bağımlılıkları
├── .gitignore                                                # Git hariç tutma kuralları
└── README.md                                                 # Proje dokümantasyonu
```

