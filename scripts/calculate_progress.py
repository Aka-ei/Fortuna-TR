#!/usr/bin/env python3
"""
Kullanım:
  python metin_say.py dosya.txt                      # sadece metin sayısı
  python metin_say.py ceviri.txt ornek.txt           # çeviri + örnek karşılaştırma
  python metin_say.py ceviri.txt ornek.txt --liste   # kalan label'ları da yazdır
  python metin_say.py ceviri.txt ornek.txt --min 2   # en az 2 karakterlik metinleri say
"""
import re
import sys
import argparse

# Bir girdi: "---\nlabel: X\n...öznitelikler...\n---\nmetin" (sonraki "---\nlabel:" veya dosya sonuna kadar)
ENTRY_RE = re.compile(
    r'^---\n'
    r'label:[ \t]*(?P<label>[^\n]*)\n'
    r'(?P<header>.*?)'
    r'^---\n'
    r'(?P<text>.*?)'
    r'(?=^---\nlabel:|\Z)',
    re.MULTILINE | re.DOTALL,
)


def parse(path):
    """Dosyayı okuyup {label: metin} sözlüğü döndürür (tüm girdiler, filtrelenmemiş)."""
    with open(path, encoding='utf-8-sig') as f:
        data = f.read().replace('\r\n', '\n')
    entries = {}
    for m in ENTRY_RE.finditer(data):
        entries[m.group('label').strip()] = m.group('text').strip()
    return entries


def valid(text, min_len):
    """Boş veya çok kısa (varsayılan: 1 karakter) metinleri eler."""
    return len(text) >= min_len


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dosya', help='Sayılacak (çevrilen) dosya')
    ap.add_argument('ornek', nargs='?', help='Örnek (kaynak) dosya')
    ap.add_argument('--min', type=int, default=2,
                    help='Geçerli sayılacak en kısa metin uzunluğu (varsayılan 2)')
    ap.add_argument('--liste', action='store_true', help='Kalan label\'ları listele')
    args = ap.parse_args()

    cur = parse(args.dosya)
    cur_valid = {k: v for k, v in cur.items() if valid(v, args.min)}

    print(f'Dosya                 : {args.dosya}')
    print(f'Toplam girdi          : {len(cur)}')
    print(f'Yok sayılan (boş/kısa): {len(cur) - len(cur_valid)}')
    print(f'Geçerli metin sayısı  : {len(cur_valid)}')

    if not args.ornek:
        return

    src = parse(args.ornek)
    src_valid = {k: v for k, v in src.items() if valid(v, args.min)}

    # Örnekte geçerli olup çeviride hâlâ aynı olan metinler -> değiştirilmesi gerekenler
    ayni = [k for k, v in src_valid.items() if k in cur and cur[k] == v]
    # Örnekte geçerli olup çeviri dosyasında hiç olmayan label'lar
    eksik = [k for k in src_valid if k not in cur]
    # Çevrilmiş sayılanlar
    cevrilmis = [k for k, v in src_valid.items() if k in cur and cur[k] != v]

    print()
    print(f'Örnek dosya           : {args.ornek}')
    print(f'Örnekte geçerli metin : {len(src_valid)}')
    print(f'Değiştirilmiş         : {len(cevrilmis)}')
    print(f'Hâlâ örnekle aynı     : {len(ayni)}   <- değiştirilmesi gerekenler')
    print(f'Çeviri dosyasında yok : {len(eksik)}')
    print(f'Toplam kalan          : {len(ayni) + len(eksik)}')
    print(f'İlerleme              : {len(cevrilmis)/len(cur_valid)}')

    if args.liste:
        if ayni:
            print('\n[Örnekle aynı kalanlar]')
            for k in ayni:
                print(f'  {k}: {src_valid[k]!r}')
        if eksik:
            print('\n[Eksik label\'lar]')
            for k in eksik:
                print(f'  {k}')


if __name__ == '__main__':
    sys.exit(main())