#!/usr/bin/env bash
# Re-render the README pictures: .github/<name>.html -> .github/<name>.png
#
# Usage:  bash tools/render-images.sh [name ...]     (no names = every picture below)
#         CHROME=/path/to/chrome bash tools/render-images.sh two-plugins
#         QUANTIZE=1 bash tools/render-images.sh      (also reduce to a 256-colour palette)
#
# Not part of verify-all.sh: CI has no Chrome. Run it by hand after editing a picture's HTML,
# then commit the PNG with the HTML.
#
# How each picture is sized (the method was never recorded, so this is inferred from the HTML
# and from the committed PNGs):
#   social-preview       1280x640 window, scale 1 -> 1280x640 (fixed size in its own CSS)
#   arrows-before-after  width is the body width its own CSS sets, measured from the page, scale 1
#   every other diagram  body is 1400px wide (base.css), scale 2000/1400 -> 2000px wide
# Height is not fixed in the CSS. The script loads the page once, reads the document height
# (and, for arrows-before-after, the body width), then takes the screenshot with a window of
# exactly that size.
#
# Bottom margin (measured 2026-10-19). Each diagram's height is its deepest content plus the
# 48 CSS px of bottom padding its own CSS declares, and that is what the screenshot comes out as.
# The committed PNGs disagree with that CSS and with each other: five of the six diagrams end on
# 37-38 background rows at 2000 px (about 26 CSS px), two-plugins on 67 (about 47). No measuring
# rule reproduces both, so the script does not measure differently. It trims every re-render
# (all but social-preview, whose size is fixed) to one margin of BOTTOM_CSS x scale rows through
# tools/png-trim.py: 37 rows at 2000 px wide, 26 at scale 1. A picture whose own margin is
# already that small is left as it is. The report line shows the trailing row count and the
# committed picture's size, so a re-render can be checked against it before committing.
#
# The trailing size report uses `sips`, which only macOS has; elsewhere it is skipped (an
# unguarded call would stop the script after the first picture under `set -e`).
#
# 256-colour step: four of the eight committed PNGs are 8-bit palette images, four are RGB, so
# the old step was applied by hand and not to every file. `pngquant` was not installed when this
# was written, so palette reduction is an optional post-step (QUANTIZE=1, needs `pngquant`).
# Without it the PNGs are plain RGB and larger, but look the same.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIR="$ROOT/.github"
# Bottom margin every trimmed picture ends on, in CSS px; see the header.
BOTTOM_CSS=26
ALL=(arrows-before-after config-layers context-table lint-catches prep-stubs qa-report social-preview two-plugins)

find_chrome() {
  local c
  if [ -n "${CHROME:-}" ] && [ -x "$CHROME" ]; then echo "$CHROME"; return 0; fi
  for c in \
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    "$(command -v google-chrome 2>/dev/null || true)" \
    "$(command -v google-chrome-stable 2>/dev/null || true)" \
    "$(command -v chromium 2>/dev/null || true)" \
    "$(command -v chromium-browser 2>/dev/null || true)"; do
    if [ -n "$c" ] && [ -x "$c" ]; then echo "$c"; return 0; fi
  done
  return 1
}

if ! CHROME_BIN="$(find_chrome)"; then
  echo "render-images: no Chrome or Chromium binary found." >&2
  echo "Install Google Chrome, or point CHROME=/path/to/chrome at one." >&2
  exit 1
fi

names=("$@")
[ ${#names[@]} -eq 0 ] && names=("${ALL[@]}")

render() {
  local name="$1" html="$DIR/$1.html" png="$DIR/$1.png"
  if [ ! -f "$html" ]; then echo "render-images: $html not found" >&2; return 1; fi

  local width height scale
  case "$name" in
    social-preview)      width=1280; height=640;  scale=1 ;;
    arrows-before-after) width="";   height="";   scale=1 ;;
    *)                   width=1400; height="";   scale=$(awk 'BEGIN{printf "%.6f", 2000/1400}') ;;
  esac

  if [ -z "$height" ] || [ -z "$width" ]; then
    # Measure: a throwaway copy that writes the body size into <title>, then dump the DOM.
    # A picture with no fixed width is probed in a wide window and takes the body width from the page.
    local probe="$DIR/.probe-$name.html" probe_w="${width:-2000}" measured
    { cat "$html"; echo '<script>var r=document.body.getBoundingClientRect();document.title="M="+Math.ceil(r.width)+"x"+Math.ceil(r.height)</script>'; } > "$probe"
    measured="$("$CHROME_BIN" --headless=new --disable-gpu --hide-scrollbars \
                --window-size="$probe_w,2000" --virtual-time-budget=2000 --dump-dom \
                "file://$probe" 2>/dev/null | sed -n 's/.*<title>M=\([0-9]*x[0-9]*\)<\/title>.*/\1/p' | head -1)"
    rm -f "$probe"
    if [ -z "$measured" ]; then echo "render-images: could not measure $name" >&2; return 1; fi
    if [ -z "$width" ]; then width="${measured%x*}"; fi
    height="${measured#*x}"
  fi

  "$CHROME_BIN" --headless=new --disable-gpu --hide-scrollbars \
    --force-device-scale-factor="$scale" --window-size="$width,$height" \
    --screenshot="$png" "file://$html" >/dev/null 2>&1

  if [ "$name" != "social-preview" ]; then
    local keep
    keep="$(awk -v c="$BOTTOM_CSS" -v s="$scale" 'BEGIN{printf "%d", c*s+0.5}')"
    python3 "$ROOT/tools/png-trim.py" "$png" --keep "$keep" >/dev/null
  fi

  if [ "${QUANTIZE:-0}" = "1" ]; then
    if command -v pngquant >/dev/null 2>&1; then
      pngquant --force --ext .png 256 "$png"
    else
      echo "render-images: QUANTIZE=1 but pngquant is not installed; left $name as RGB" >&2
    fi
  fi

  local trailing committed="n/a" old
  trailing="$(python3 "$ROOT/tools/png-trim.py" "$png" --count 2>/dev/null | sed -n 's/.*trailing=//p' || true)"
  old="$(git -C "$ROOT" show "HEAD:.github/$name.png" 2>/dev/null \
         | python3 -c 'import struct,sys; b=sys.stdin.buffer.read(24); print("%dx%d" % struct.unpack(">II", b[16:24]))' 2>/dev/null || true)"
  [ -n "$old" ] && committed="$old"
  local size="(size not reported: no sips here)"
  if command -v sips >/dev/null 2>&1; then
    local w h
    w="$(sips -g pixelWidth "$png" | awk '/pixelWidth/{print $2}')"
    h="$(sips -g pixelHeight "$png" | awk '/pixelHeight/{print $2}')"
    size="${w}x${h}"
  fi
  echo "rendered $name.png $size trailing=${trailing:-n/a} committed=$committed"
}

for n in "${names[@]}"; do render "$n"; done
