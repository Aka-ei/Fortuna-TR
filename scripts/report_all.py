#!/usr/bin/env python3
"""
Dosya adı: ilerleme_rapor.py   (msbt_say.py ile aynı klasörde olmalı)

Kullanım:
  python ilerleme_rapor.py ceviri_klasoru ornek_klasoru
  python ilerleme_rapor.py ceviri_klasoru ornek_klasoru --cikti rapor --min 2
  python ilerleme_rapor.py ceviri_klasoru ornek_klasoru --genislik 2400
"""
import os, html
import colorsys
import argparse
from PIL import Image, ImageDraw, ImageFont
from calc_all import load_folder, valid

FONT_ADAYLARI = [
    'C:/Windows/Fonts/segoeui.ttf', 'C:/Windows/Fonts/arial.ttf',
    '/Library/Fonts/Arial.ttf', '/System/Library/Fonts/Supplemental/Arial.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    '/usr/share/fonts/TTF/DejaVuSans.ttf',
]
FONT_KALIN_ADAYLARI = [
    'C:/Windows/Fonts/segoeuib.ttf', 'C:/Windows/Fonts/arialbd.ttf',
    '/Library/Fonts/Arial Bold.ttf', '/System/Library/Fonts/Supplemental/Arial Bold.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    '/usr/share/fonts/TTF/DejaVuSans-Bold.ttf',
]


def font(size, kalin=False):
    for p in (FONT_KALIN_ADAYLARI if kalin else FONT_ADAYLARI):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    try:
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()


# ---------- İstatistik ----------
def collect(cur, src, mn):
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


def renk(p):
    """%0 kırmızı -> %100 yeşil (HTML sürümüyle aynı: hsl(p*1.2, 60%, 38%))"""
    r, g, b = colorsys.hls_to_rgb((p * 1.2) / 360.0, 0.38, 0.60)
    return int(r * 255), int(g * 255), int(b * 255)


# ---------- Squarified treemap ----------
def _worst(row, side):
    s = sum(row)
    return max(max(side * side * r / (s * s), (s * s) / (side * side * r)) for r in row)


def _place(row, x, y, w, h, out):
    s = sum(row)
    if w >= h:
        cw = s / h
        yy = y
        for r in row:
            rh = r / cw
            out.append((x, yy, cw, rh))
            yy += rh
        return x + cw, y, w - cw, h
    rh = s / w
    xx = x
    for r in row:
        rw = r / rh
        out.append((xx, y, rw, rh))
        xx += rw
    return x, y + rh, w, h - rh


def squarify(values, w, h):
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


# ---------- Çizim ----------
def sigdir(d, text, f, maxw):
    """Metni maxw genişliğine sığacak şekilde kısaltır."""
    if d.textlength(text, font=f) <= maxw:
        return text
    while len(text) > 1 and d.textlength(text + '…', font=f) > maxw:
        text = text[:-1]
    return text + '…'


def golgeli(d, xy, text, f, fill=(255, 255, 255)):
    x, y = xy
    d.text((x + 1, y + 1), text, font=f, fill=(0, 0, 0))
    d.text((x, y), text, font=f, fill=fill)


def write_jpg(path, stats, overall, W):
    BG = (27, 27, 31)
    HEADER = int(W * 0.075)
    TH = int(W * 0.58)            # treemap yüksekliği
    H = HEADER + TH + 12
    img = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(img)

    # Başlık
    d.text((16, 10), f'Çeviri İlerlemesi: %{overall:.1f}', font=font(int(W * 0.022), True),
           fill=(238, 238, 238))
    d.text((16, 10 + int(W * 0.03)), 'Alan = metin sayısı  ·  Renk = tamamlanma yüzdesi',
           font=font(int(W * 0.0105)), fill=(170, 170, 175))

    # Renk skalası (sağ üst)
    lw, lh = int(W * 0.2), int(W * 0.01)
    lx, ly = W - lw - 16, 18
    for i in range(lw):
        d.line([(lx + i, ly), (lx + i, ly + lh)], fill=renk(100.0 * i / lw))
    sf = font(int(W * 0.0085))
    d.text((lx, ly + lh + 4), '%0', font=sf, fill=(200, 200, 200))
    d.text((lx + lw - d.textlength('%100', font=sf), ly + lh + 4), '%100', font=sf,
           fill=(200, 200, 200))

    # Treemap
    items = sorted(stats.items(), key=lambda kv: -kv[1]['total'])
    rects = squarify([s['total'] for _, s in items], W - 24, TH)
    ox, oy = 12, HEADER
    fb, fs = font(int(W * 0.0095), True), font(int(W * 0.0085))
    for (name, s), (x, y, w, h) in zip(items, rects):
        p = pct(s['done'], s['total'])
        x0, y0 = ox + x, oy + y
        x1, y1 = x0 + w, y0 + h
        d.rectangle([x0, y0, x1, y1], fill=renk(p), outline=BG, width=1)
        if w < 46 or h < 18:
            continue
        pad = 5
        maxw = w - 2 * pad
        golgeli(d, (x0 + pad, y0 + 3), sigdir(d, os.path.basename(name), fb, maxw), fb)
        if h >= 38:
            golgeli(d, (x0 + pad, y0 + 3 + int(W * 0.0125)),
                    sigdir(d, f'%{p:.0f} · {s["done"]}/{s["total"]}', fs, maxw), fs)

    img.save(path, 'JPEG', quality=92)

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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('klasor', help='Çevrilen dosyaların klasörü')
    ap.add_argument('ornek', help='Örnek (kaynak) klasör')
    ap.add_argument('--min', type=int, default=2, help='Geçerli en kısa metin uzunluğu')
    ap.add_argument('--cikti', default='ilerleme', help='Çıktı dosya adı (uzantısız)')
    ap.add_argument('--genislik', type=int, default=1600, help='Görsel genişliği (px)')
    a = ap.parse_args()

    cur = load_folder(a.klasor)
    src = load_folder(a.ornek)
    stats = collect(cur, src, a.min)
    if not stats:
        print('Örnekte geçerli metin bulunamadı.')
        return

    T = sum(s['total'] for s in stats.values())
    D = sum(s['done'] for s in stats.values())
    overall = pct(D, T)

    write_html(f"docs/{a.cikti}.html", stats, overall)

    out = f"assets/{a.cikti}.jpg"
    write_jpg(out, stats, overall, a.genislik)
    print(f'Genel ilerleme: %{overall:.1f}  ({D}/{T}, kalan {T - D})')
    print(f'Yazıldı: {out}')


if __name__ == '__main__':
    main()