#!/usr/bin/env python3

import os, shutil
import struct
import argparse
import zstandard

OUT_DIR = '_cikarilan'


# ---------- ZST ----------
def extract_zst(folder):
    """Klasördeki tüm .zst dosyalarını açar. {göreli_yol: tam_yol} döndürür."""
    files = {}
    dctx = zstandard.ZstdDecompressor()
    for root, dirs, names in os.walk(folder):
        dirs[:] = [d for d in dirs if d != OUT_DIR]
        for n in names:
            full = os.path.join(root, n)
            rel = os.path.relpath(full, folder)
            if n.lower().endswith('.zst'):
                rel = rel[:-4]
                out = os.path.join(folder, OUT_DIR, rel)
                if not os.path.exists(out):
                    os.makedirs(os.path.dirname(out), exist_ok=True)
                    with open(full, 'rb') as fi, open(out, 'wb') as fo:
                        dctx.copy_stream(fi, fo)
                files[rel] = out
            else:
                files.setdefault(rel, full)
    return files


# ---------- MSBT ----------
def decode_text(raw, enc, E):
    """Ham baytları metne çevirir; kontrol kodlarını {grup.tip} olarak yazar."""
    out = []
    if enc == 1:  # UTF-16
        u = struct.unpack(E + '%dH' % (len(raw) // 2), raw[:len(raw) // 2 * 2])
        i = 0
        while i < len(u):
            c = u[i]
            if c == 0:
                break
            if c == 0x0E and i + 3 < len(u):
                out.append('{%d.%d}' % (u[i + 1], u[i + 2]))
                i += 4 + u[i + 3] // 2
                continue
            if c == 0x0F:
                out.append('{/}')
                i += 3
                continue
            if 0xD800 <= c < 0xDC00 and i + 1 < len(u):
                out.append(chr(0x10000 + ((c - 0xD800) << 10) + (u[i + 1] - 0xDC00)))
                i += 2
                continue
            out.append(chr(c))
            i += 1
    else:  # UTF-8 (enc == 0)
        b = raw.split(b'\x00')[0] if b'\x0e' not in raw else raw
        i = 0
        buf = bytearray()
        while i < len(b):
            if b[i] == 0x0E and i + 6 < len(b):
                out.append(buf.decode('utf-8', 'replace')); buf.clear()
                g, t, s = struct.unpack(E + 'HHH', b[i + 1:i + 7])
                out.append('{%d.%d}' % (g, t))
                i += 7 + s
                continue
            if b[i] == 0:
                break
            buf.append(b[i])
            i += 1
        out.append(buf.decode('utf-8', 'replace'))
    return ''.join(out)


def parse_msbt(path):
    """MSBT ise {label: metin} döndürür, değilse None."""
    with open(path, 'rb') as f:
        d = f.read()
    if d[:8] != b'MsgStdBn':
        return None
    E = '>' if d[8:10] == b'\xFE\xFF' else '<'
    enc = d[0x0C]
    n_sec = struct.unpack_from(E + 'H', d, 0x0E)[0]

    sections = {}
    pos = 0x20
    for _ in range(n_sec):
        magic = d[pos:pos + 4]
        size = struct.unpack_from(E + 'I', d, pos + 4)[0]
        sections[magic] = d[pos + 16:pos + 16 + size]
        pos = (pos + 16 + size + 15) & ~15

    # TXT2
    texts = []
    t = sections.get(b'TXT2')
    if t:
        n = struct.unpack_from(E + 'I', t, 0)[0]
        offs = struct.unpack_from(E + '%dI' % n, t, 4)
        for i in range(n):
            e = offs[i + 1] if i + 1 < n else len(t)
            texts.append(decode_text(t[offs[i]:e], enc, E))

    # LBL1
    names = {}
    l = sections.get(b'LBL1')
    if l:
        groups = struct.unpack_from(E + 'I', l, 0)[0]
        for g in range(groups):
            cnt, off = struct.unpack_from(E + 'II', l, 4 + g * 8)
            p = off
            for _ in range(cnt):
                ln = l[p]
                name = l[p + 1:p + 1 + ln].decode('ascii', 'replace')
                idx = struct.unpack_from(E + 'I', l, p + 1 + ln)[0]
                names[idx] = name
                p += 5 + ln

    return {names.get(i, '#%d' % i): s.strip() for i, s in enumerate(texts)}


def load_folder(folder):
    """{göreli_dosya: {label: metin}}"""
    
    tmp = os.path.join(folder, OUT_DIR)
    shutil.rmtree(tmp, ignore_errors=True)
    result = {}
    try:
        for rel, full in extract_zst(folder).items():
            try:
                m = parse_msbt(full)
            except Exception as ex:
                print(f'  ! okunamadı: {rel} ({ex})')
                continue
            if m is not None:
                result[rel] = m
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return result


def valid(t, mn):
    return len(t) >= mn


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('klasor', help='Çevrilen dosyaların klasörü')
    ap.add_argument('ornek', nargs='?', help='Örnek (kaynak) klasör')
    ap.add_argument('--min', type=int, default=2, help='Geçerli en kısa metin uzunluğu')
    ap.add_argument('--liste', action='store_true', help='Kalanları listele')
    a = ap.parse_args()

    cur = load_folder(a.klasor)
    tot_all = sum(len(v) for v in cur.values())
    tot_valid = sum(1 for v in cur.values() for t in v.values() if valid(t, a.min))
    print(f'MSBT dosyası          : {len(cur)}')
    print(f'Toplam girdi          : {tot_all}')
    print(f'Yok sayılan (boş/kısa): {tot_all - tot_valid}')
    print(f'Geçerli metin sayısı  : {tot_valid}')

    if not a.ornek:
        return

    src = load_folder(a.ornek)
    same, missing, done, src_valid = [], [], 0, 0
    for f, labels in src.items():
        for k, v in labels.items():
            if not valid(v, a.min):
                continue
            src_valid += 1
            c = cur.get(f, {}).get(k)
            if c is None:
                missing.append((f, k))
            elif c == v:
                same.append((f, k, v))
            else:
                done += 1

    print(f'\nÖrnekte geçerli metin : {src_valid}')
    print(f'Değiştirilmiş         : {done}')
    print(f'Hâlâ örnekle aynı     : {len(same)}   <- değiştirilmesi gerekenler')
    print(f'Çeviride bulunmayan   : {len(missing)}')
    print(f'Toplam kalan          : {len(same) + len(missing)}')

    # Dosya bazlı özet
    per = {}
    for f, k, v in same:
        per[f] = per.get(f, 0) + 1
    for f, k in missing:
        per[f] = per.get(f, 0) + 1
    if per:
        print('\n[Dosya bazında kalan]')
        for f, c in sorted(per.items(), key=lambda x: -x[1]):
            print(f'  {c:5d}  {f}')

    if a.liste:
        print('\n[Örnekle aynı kalanlar]')
        for f, k, v in same:
            print(f'  {f} :: {k} = {v!r}')
        print('\n[Eksik label\'lar]')
        for f, k in missing:
            print(f'  {f} :: {k}')


if __name__ == '__main__':
    main()