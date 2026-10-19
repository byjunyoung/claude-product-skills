#!/usr/bin/env python3
"""Fixtures for tools/png-trim.py — trimming a picture's trailing background rows.

    python3 tools/test/png-trim.test.py

Each case writes a small PNG with a stdlib writer, runs the script as a subprocess, and reads
the result back.
"""
import binascii, os, struct, subprocess, sys, tempfile, zlib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "tools" / "png-trim.py"
failures = []


def check(label, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + label + (f"  — {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(label)


def chunk(kind, data):
    return (struct.pack(">I", len(data)) + kind + data
            + struct.pack(">I", binascii.crc32(kind + data) & 0xFFFFFFFF))


def make_png(w, rows, ctype=2, filt=0):
    """rows: raw pixel byte strings. filt 2 (Up) proves the script unfilters before comparing."""
    bpp = {2: 3, 6: 4, 3: 1}[ctype]
    raw = b""
    prev = bytes(w * bpp)
    for r in rows:
        if filt == 2:
            raw += b"\x02" + bytes((a - b) & 255 for a, b in zip(r, prev))
        else:
            raw += b"\x00" + r
        prev = r
    out = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, len(rows), 8, ctype, 0, 0, 0))
    if ctype == 3:
        out += chunk(b"PLTE", b"\x00\x00\x00\xff\xff\xff")
    return out + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def read_size(path):
    b = Path(path).read_bytes()
    return struct.unpack(">II", b[16:24])


def run(*args):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env=env)


def rows_for(w, black, white, bpp):
    return [bytes([0, 0, 0, 255][:bpp]) * w] * black + [bytes([255] * bpp) * w] * white


with tempfile.TemporaryDirectory() as t:
    t = Path(t)

    for label, ctype, bpp in (("keep trims trailing rows", 2, 3), ("RGBA is handled", 6, 4)):
        p = t / f"a{ctype}.png"
        p.write_bytes(make_png(10, rows_for(10, 10, 40, bpp), ctype))
        r = run(str(p), "--keep", "5")
        c = run(str(p), "--count")
        check(label, r.returncode == 0 and read_size(p) == (10, 15) and "trailing=5" in c.stdout
              and "10x50 -> 10x15" in r.stdout, r.stdout + r.stderr + c.stdout)

    p = t / "up.png"
    p.write_bytes(make_png(10, rows_for(10, 10, 40, 3), 2, filt=2))
    run(str(p), "--keep", "5")
    check("filtered rows are compared unfiltered", read_size(p) == (10, 15))

    p = t / "short.png"
    data = make_png(10, rows_for(10, 10, 2, 3))
    p.write_bytes(data)
    r = run(str(p), "--keep", "5")
    check("keep never adds rows", r.returncode == 0 and p.read_bytes() == data, r.stdout + r.stderr)

    p = t / "pal.png"
    data = make_png(10, rows_for(10, 10, 40, 1), 3)
    p.write_bytes(data)
    r = run(str(p), "--keep", "5")
    check("palette PNG -> exit 2, untouched", r.returncode == 2 and "unsupported PNG" in r.stderr
          and p.read_bytes() == data, r.stdout + r.stderr)

sys.exit(1 if failures else 0)
