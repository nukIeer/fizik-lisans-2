#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import json
import pandas as pd
from tabulate import tabulate
from colorama import Fore, Style, init
import shutil

# Colorama başlat
init(autoreset=True)

def create_release_with_pdfs():
    """GitHub release için PDF dosyalarını toplar ve oluşturur."""
    release_folder = 'release_pdfs'
    os.makedirs(release_folder, exist_ok=True)
    
    # JSON dosyasından dosya listesini oku
    with open('file_list.json', 'r') as f:
        file_list = json.load(f)
    
    # PDF dosyalarını filtrele ve 'release_pdfs' klasörüne kopyala
    for file_info in file_list:
        filename = file_info['name']
        filepath = file_info['path']
        
        if filepath.endswith(".pdf"):
            shutil.copy(filepath, os.path.join(release_folder, filename))
    
    print(f"{Fore.CYAN}📦 PDF dosyaları {release_folder} klasörüne kopyalandı.")

def main():
    # JSON dosyadan dosya listesini oku
    with open('file_list.json', 'r') as f:
        file_list = json.load(f)
    
    # Ders kodu düzeni (örn: FZKT2402_MF_H03_S1_KutleOrani)
    pattern = r"([A-Z]+\d+)_([A-Z]+)_H(\d+)(?:_S(\d+))?(?:_([A-Za-z0-9]+))?"
    
    # Dosya bilgilerini çıkar
    file_data = []
    
    for file_info in file_list:
        filename = file_info['name']
        filepath = file_info['path']
        match = re.match(pattern, filename)
        
        if match:
            ders_kodu = match.group(1)
            ders_kisa = match.group(2)
            hafta = int(match.group(3))
            slayt = int(match.group(4)) if match.group(4) else None
            konu = match.group(5) if match.group(5) else None
            
            dosya_tipi = "Diğer"
            if "ODEV" in filename:
                if filepath.endswith(".pdf"):
                    dosya_tipi = "Ödev PDF"
                else:
                    dosya_tipi = "Ödev Çözüm"
            elif filepath.endswith(".pdf"):
                dosya_tipi = "Slayt PDF"
            elif filepath.endswith(".tex"):
                dosya_tipi = "LaTeX Kaynak"
            
            file_data.append({
                "DersKodu": ders_kodu, 
                "DersKisa": ders_kisa,
                "Hafta": hafta,
                "Slayt": slayt,
                "Konu": konu,
                "DosyaTipi": dosya_tipi,
                "DosyaAdi": filename,
                "DosyaYolu": filepath
            })
    
    # DataFrame oluştur
    df = pd.DataFrame(file_data)
    
    # Analizler
    sorunlar = []
    
    if not df.empty:
        # Mevcut haftaları bul
        mevcut_haftalar = sorted(df["Hafta"].unique())
        
        # Eksik hafta kontrolü
        if mevcut_haftalar:
            olması_gereken_haftalar = list(range(1, max(mevcut_haftalar) + 1))
            eksik_haftalar = [h for h in olması_gereken_haftalar if h not in mevcut_haftalar]
            
            if eksik_haftalar:
                sorunlar.append(f"⚠️ Eksik haftalar: {', '.join(map(str, eksik_haftalar))}")
        
        # Ödev PDF'leri ve çözümleri kontrol et
        odev_pdf = df[df["DosyaTipi"] == "Ödev PDF"]
        odev_cozum = df[df["DosyaTipi"] == "Ödev Çözüm"]
        
        for _, row in odev_pdf.iterrows():
            hafta = row["Hafta"]
            odev_adi = row["DosyaAdi"].replace(".pdf", "")
            
            # Ödev çözümü var mı kontrol et
            if not any(odev_adi == cozum["DosyaAdi"] for _, cozum in odev_cozum.iterrows()):
                sorunlar.append(f"❌ Hafta {hafta}: '{odev_adi}' için çözüm dosyası eksik.")
        
        # Slayt PDF'leri için kaynak dosyaları kontrol et
        slayt_pdf = df[df["DosyaTipi"] == "Slayt PDF"]
        latex_kaynaklar = df[df["DosyaTipi"] == "LaTeX Kaynak"]
        
        for _, row in slayt_pdf.iterrows():
            hafta = row["Hafta"]
            slayt = row["Slayt"]
            slayt_adi = row["DosyaAdi"].replace(".pdf", "")
            
            # LaTeX kaynak var mı kontrol et
            kaynak_var = any(
                (row["Hafta"] == kaynak["Hafta"] and row["Slayt"] == kaynak["Slayt"])
                for _, kaynak in latex_kaynaklar.iterrows()
            )
            
            if not kaynak_var:
                sorunlar.append(f"⚠️ Hafta {hafta} Slayt {slayt}: '{slayt_adi}' için LaTeX kaynak dosyası eksik.")

    # Özet tablo oluştur
    ozet_data = []
    
    if not df.empty:
        for hafta in sorted(df["Hafta"].unique()):
            hafta_data = df[df["Hafta"] == hafta]
            
            # Slaytlar
            slaytlar = sorted(hafta_data[hafta_data["DosyaTipi"] == "Slayt PDF"]["Slayt"].dropna().unique())
            slayt_str = ", ".join(map(str, slaytlar)) if slaytlar else "❌"
            
            # Ödevler
            odevler = hafta_data[hafta_data["DosyaTipi"] == "Ödev PDF"]["DosyaAdi"].tolist()
            odev_str = ", ".join(odevler) if odevler else "❌"
            
            # Çözümler
            cozumler = hafta_data[hafta_data["DosyaTipi"] == "Ödev Çözüm"]["DosyaAdi"].tolist()
            cozum_str = ", ".join(cozumler) if cozumler else "❌"
            
            ozet_data.append([
                hafta, 
                slayt_str, 
                odev_str if odevler else "❌", 
                "✅" if cozumler else "❌"
            ])
    
    # Rapor oluştur
    with open("rapor.md", "w", encoding="utf-8") as f:
        f.write("# Ders Notları Kontrol Raporu\n\n")
        
        if sorunlar:
            f.write("## 🚨 Tespit Edilen Sorunlar\n\n")
            for sorun in sorunlar:
                f.write(f"- {sorun}\n")
            f.write("\n")
        else:
            f.write("## ✅ Tüm kontroller başarılı! Herhangi bir sorun bulunamadı.\n\n")
        
        f.write("## 📊 Haftalık Özet\n\n")
        
        if ozet_data:
            ozet_tablo = tabulate(
                ozet_data,
                headers=["Hafta", "Slaytlar", "Ödevler", "Çözümler"],
                tablefmt="pipe"
            )
            f.write(ozet_tablo + "\n\n")
        else:
            f.write("Henüz ders materyali yok veya dosya adı deseni tanınmadı.\n\n")
        
        f.write("## 📚 Dosya Listesi\n\n")
        
        if not df.empty:
            dosya_listesi = df[["Hafta", "Slayt", "DosyaTipi", "DosyaAdi"]].sort_values(
                by=["Hafta", "Slayt", "DosyaTipi"]
            )
            
            dosya_tablo = tabulate(
                dosya_listesi.values.tolist(),
                headers=["Hafta", "Slayt", "Tür", "Dosya Adı"],
                tablefmt="pipe"
            )
            f.write(dosya_tablo + "\n")
        else:
            f.write("Henüz dosya yok veya dosya adı deseni tanınmadı.\n")
    
    # GitHub Actions çıktısı için
    if 'GITHUB_OUTPUT' in os.environ:
        with open(os.environ['GITHUB_OUTPUT'], 'a') as fh:
            sorun_sayisi = len(sorunlar)
            fh.write(f'sorun_sayisi={sorun_sayisi}\n')
            fh.write(f'rapor_olusturuldu=true\n')

    # PDF'leri release olarak sunma
    create_release_with_pdfs()

if __name__ == "__main__":
    main()
