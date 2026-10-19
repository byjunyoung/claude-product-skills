#!/usr/bin/env python3
"""Trim a PNG's trailing background rows down to a fixed count.

    python3 tools/png-trim.py FILE --keep N    rewrite FILE so exactly N trailing rows equal its
                                               last row; prints "WxH -> WxH2"
    python3 tools/png-trim.py FILE --count     print "WxH trailing=n"; never writes

A file with N or fewer trailing rows is left byte for byte. Only non-interlaced 8-bit RGB (colour
type 2) and RGBA (6) are handled, which is what headless Chrome writes; anything else exits 2 with
"unsupported PNG" and the file is untouched. Standard library only.
"""
import binascii
import struct
import sys
import zlib

SIG = b"\x89PNG\r\n\x1a\n"
BPP = {2: 3, 6: 4}


class Unsupported(Exception):
    pass


def _chunks(data):
    pos = len(SIG)
    while pos < len(data):
        n = struct.unpack(">I", data[pos:pos + 4])[0]
        yield data[pos + 4:pos + 8], data[pos + 8:pos + 8 + n]
        pos += 12 + n


def _chunk(kind, body):
    return (struct.pack(">I", len(body)) + kind + body
            + struct.pack(">I", binascii.crc32(kind + body) & 0xFFFFFFFF))


def _paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    return a if pa <= pb and pa <= pc else (b if pb <= pc else c)


def _unfilter(raw, w, h, bpp):
    stride = w * bpp
    if len(raw) != h * (stride + 1):
        raise Unsupported
    rows, prev = [], bytearray(stride)
    for y in range(h):
        ft = raw[y * (stride + 1)]
        cur = bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        if ft == 0:
            pass
        elif ft == 1:
            for i in range(bpp, stride):
                cur[i] = (cur[i] + cur[i - bpp]) & 255
        elif ft == 2:
            for i in range(stride):
                cur[i] = (cur[i] + prev[i]) & 255
        elif ft == 3:
            for i in range(stride):
                left = cur[i - bpp] if i >= bpp else 0
                cur[i] = (cur[i] + ((left + prev[i]) >> 1)) & 255
        elif ft == 4:
            for i in range(stride):
                left = cur[i - bpp] if i >= bpp else 0
                ul = prev[i - bpp] if i >= bpp else 0
                cur[i] = (cur[i] + _paeth(left, prev[i], ul)) & 255
        else:
            raise Unsupported
        rows.append(bytes(cur))
        prev = cur
    return rows


def trailing_rows(rows):
    """How many rows at the end equal the last row (the last row counts)."""
    n = 0
    for r in reversed(rows):
        if r != rows[-1]:
            break
        n += 1
    return n


def parse(data):
    if data[:8] != SIG:
        raise Unsupported
    ihdr, idat = None, []
    for kind, body in _chunks(data):
        if kind == b"IHDR":
            ihdr = body
        elif kind == b"IDAT":
            idat.append(body)
    if ihdr is None or not idat:
        raise Unsupported
    w, h, depth, ctype, _comp, _filt, interlace = struct.unpack(">IIBBBBB", ihdr)
    if depth != 8 or ctype not in BPP or interlace != 0 or h == 0:
        raise Unsupported
    try:
        raw = zlib.decompress(b"".join(idat))
    except zlib.error:
        raise Unsupported
    return w, h, ctype, _unfilter(raw, w, h, BPP[ctype])


def rewrite(data, w, h2, ctype, rows):
    """Same chunks as `data`, IDAT replaced by one re-filtered (type 0) stream, height updated."""
    raw = b"".join(b"\x00" + r for r in rows)
    out, wrote = [SIG], False
    for kind, body in _chunks(data):
        if kind == b"IHDR":
            body = struct.pack(">II", w, h2) + body[8:]
        if kind == b"IDAT":
            if not wrote:
                out.append(_chunk(b"IDAT", zlib.compress(raw, 9)))
                wrote = True
            continue
        out.append(_chunk(kind, body))
    return b"".join(out)


def main(argv):
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 1
    path, mode = argv[0], argv[1]
    keep = None
    if mode == "--keep":
        if len(argv) != 3 or not argv[2].isdigit():
            print("png-trim: --keep needs a number", file=sys.stderr)
            return 1
        keep = int(argv[2])
    elif mode != "--count":
        print(__doc__, file=sys.stderr)
        return 1
    with open(path, "rb") as f:
        data = f.read()
    try:
        w, h, ctype, rows = parse(data)
    except (Unsupported, struct.error):
        print("unsupported PNG", file=sys.stderr)
        return 2
    n = trailing_rows(rows)
    if mode == "--count":
        print(f"{w}x{h} trailing={n}")
        return 0
    if n <= keep:
        print(f"{w}x{h} -> {w}x{h}")
        return 0
    rows = rows[:h - (n - keep)]
    with open(path, "wb") as f:
        f.write(rewrite(data, w, len(rows), ctype, rows))
    print(f"{w}x{h} -> {w}x{len(rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
