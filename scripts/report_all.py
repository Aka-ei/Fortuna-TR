#!/usr/bin/env python3
"""
Dosya adı: ilerleme_rapor.py   (msbt_say.py ile aynı klasörde olmalı)

Kullanım:
  python ilerleme_rapor.py ceviri_klasoru ornek_klasoru
  python ilerleme_rapor.py ceviri_klasoru ornek_klasoru --cikti rapor --min 2
"""
import os
import html
import argparse
from calc_all import load_folder, valid


# ---------- İstatistik ----------
def collect(cur, src, mn):
    """Dosya bazında {dosya: dict(total, done, same, missing)}"""
    stats = {}
    for f, labels in src.items():
        total = done = same = missing = 0
        for k, v in labels.items():
            if not valid(v, mn):
                continue
            total += 1
            c = cur.get(f, {}).get(k)
            if c is None:
                missing += 1
            elif c == v:
                same += 1
            else:
                done += 1
        if total:
            stats[f] = dict(total=total, done=done, same=same, missing=missing)
    return stats


def pct(done, total):
    return 100.0 * done / total if total else 0.0


def bar(p, n=20):
    full = round(p / 100 * n)
    return '█' * full + '░' * (n - full)


# ---------- Squarified treemap ----------
def _worst(row, side):
    s = sum(row)
    return max(max(side * side * r / (s * s), (s * s) / (side * side * r)) for r in row)


def _place(row, x, y, w, h, out):
    s = sum(row)
    if w >= h:                       # sol tarafa dikey sütun
        cw = s / h
        yy = y
        for r in row:
            rh = r / cw
            out.append((x, yy, cw, rh))
            yy += rh
        return x + cw, y, w - cw, h
    rh = s / w                       # üste yatay satır
    xx = x
    for r in row:
        rw = r / rh
        out.append((xx, y, rw, rh))
        xx += rw
    return x, y + rh, w, h - rh


def squarify(values, w, h):
    """values: azalan sıralı değerler. Aynı sırada (x,y,w,h) listesi döner."""
    total = sum(values)
    areas = [v / total * w * h for v in values]
    out, row, x, y, ww, hh = [], [], 0.0, 0.0, float(w), float(h)
    i = 0
    while i < len(areas):
        side = min(ww, hh)
        a = areas[i]
        if not row or _worst(row + [a], side) <= _worst(row, side):
            row.append(a)
            i += 1
        else:
            x, y, ww, hh = _place(row, x, y, ww, hh, out)
            row = []
    if row:
        _place(row, x, y, ww, hh, out)
    return out


# ---------- HTML ----------
def write_html(path, stats, overall):
    items = sorted(stats.items(), key=lambda kv: -kv[1]['total'])
    W, H = 1000, 600
    rects = squarify([s['total'] for _, s in items], W, H)

    boxes = []
    for (name, s), (x, y, w, h) in zip(items, rects):
        p = pct(s['done'], s['total'])
        color = f'hsl({p * 1.2:.0f},60%,38%)'
        short = os.path.basename(name)
        tip = (f'{name}\nİlerleme: %{p:.1f}\nÇevrilen: {s["done"]}/{s["total"]}\n'
               f'Aynı kalan: {s["same"]}  Eksik: {s["missing"]}')
        boxes.append(
            f'<div class="b" style="left:{x / W * 100:.4f}%;top:{y / H * 100:.4f}%;'
            f'width:{w / W * 100:.4f}%;height:{h / H * 100:.4f}%;background:{color}" '
            f'title="{html.escape(tip)}"><div class="t"><b>{html.escape(short)}</b><br>'
            f'%{p:.0f} · {s["done"]}/{s["total"]}</div></div>')

    page = f'''<!DOCTYPE html>
<html lang="tr"><head><meta charset="utf-8"><title>Çeviri İlerlemesi</title>
<style>
body{{font-family:system-ui,sans-serif;background:#1b1b1f;color:#eee;margin:24px}}
.tm{{position:relative;width:100%;max-width:1400px;aspect-ratio:{W}/{H};background:#000}}
.b{{position:absolute;box-sizing:border-box;border:1px solid #1b1b1f;overflow:hidden}}
.b:hover{{outline:2px solid #fff;z-index:2}}
.t{{padding:4px 6px;font-size:12px;line-height:1.3;color:#fff;text-shadow:0 1px 2px #000}}
.leg{{height:12px;max-width:300px;margin:8px 0;border-radius:6px;
background:linear-gradient(90deg,hsl(0,60%,38%),hsl(60,60%,38%),hsl(120,60%,38%))}}
</style></head><body>
<h2>Çeviri İlerlemesi: %{overall:.1f}</h2>
<div>Alan = metin sayısı · Renk = tamamlanma yüzdesi</div>
<div class="leg"></div><div style="max-width:300px;display:flex;justify-content:space-between;font-size:12px"><span>%0</span><span>%100</span></div><br>
<div class="tm">{''.join(boxes)}</div>
</body></html>'''
    with open(path, 'w', encoding='utf-8') as f:
        f.write(page)


# ---------- Markdown ----------
def write_md(path, stats):
    T = sum(s['total'] for s in stats.values())
    D = sum(s['done'] for s in stats.values())
    S = sum(s['same'] for s in stats.values())
    M = sum(s['missing'] for s in stats.values())
    overall = pct(D, T)

    L = ['# Çeviri İlerleme Raporu', '',
         f'**Genel: %{overall:.1f}** `{bar(overall, 30)}`', '',
         '| Toplam | Çevrilen | Aynı kalan | Eksik | Kalan |',
         '|---:|---:|---:|---:|---:|',
         f'| {T} | {D} | {S} | {M} | {S + M} |', '',
         'Treemap görünümü için `ilerleme.html` dosyasını tarayıcıda aç.', '']

    # Üst klasör özeti
    groups = {}
    for f, s in stats.items():
        g = f.replace('\\', '/').split('/')[0] if ('/' in f.replace('\\', '/')) else '(kök)'
        a = groups.setdefault(g, dict(total=0, done=0))
        a['total'] += s['total']
        a['done'] += s['done']
    if len(groups) > 1:
        L += ['## Klasör özeti', '', '| Klasör | İlerleme | Çubuk | Çevrilen / Toplam |',
              '|---|---:|---|---:|']
        for g, a in sorted(groups.items(), key=lambda kv: pct(kv[1]['done'], kv[1]['total'])):
            p = pct(a['done'], a['total'])
            L.append(f'| {g} | %{p:.1f} | `{bar(p)}` | {a["done"]} / {a["total"]} |')
        L.append('')

    # Dosya tablosu
    L += ['## Dosya bazında (en çok kalandan aza)', '',
          '| Dosya | İlerleme | Çubuk | Çevrilen / Toplam | Kalan |',
          '|---|---:|---|---:|---:|']
    for f, s in sorted(stats.items(), key=lambda kv: -(kv[1]['same'] + kv[1]['missing'])):
        p = pct(s['done'], s['total'])
        L.append(f'| {f} | %{p:.1f} | `{bar(p)}` | {s["done"]} / {s["total"]} | {s["same"] + s["missing"]} |')

    with open(path, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(L) + '\n')
    return overall


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('klasor', help='Çevrilen dosyaların klasörü')
    ap.add_argument('ornek', help='Örnek (kaynak) klasör')
    ap.add_argument('--min', type=int, default=2, help='Geçerli en kısa metin uzunluğu')
    ap.add_argument('--cikti', default='ilerleme', help='Çıktı dosya adı (uzantısız)')
    a = ap.parse_args()

    cur = load_folder(a.klasor)
    src = load_folder(a.ornek)
    stats = collect(cur, src, a.min)
    if not stats:
        print('Örnekte geçerli metin bulunamadı.')
        return

    overall = write_md(a.cikti + '.md', stats)
    write_html(a.cikti + '.html', stats, overall)

    T = sum(s['total'] for s in stats.values())
    D = sum(s['done'] for s in stats.values())
    print(f'Genel ilerleme: %{overall:.1f}  ({D}/{T}, kalan {T - D})')
    print(f'Yazıldı: {a.cikti}.md, {a.cikti}.html')


if __name__ == '__main__':
    main()