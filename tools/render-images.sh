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
#   arrows-before-after  body is 1560px wide, scale 1 -> 1560px wide
#   every other diagram  body is 1400px wide (base.css), scale 2000/1400 -> 2000px wide
# Height is not fixed in the CSS. The script loads the page once, reads the document height,
# then takes the screenshot with a window of exactly that height.
#
# Committed sizes at the time this script was written, and what the script produced:
#   picture              committed   rendered
#   arrows-before-after  1560x1345   1560x1362
#   config-layers        2000x1364   2000x1400
#   context-table        2000x1362   2000x1400
#   lint-catches         2000x1804   2000x1844
#   prep-stubs           2000x2160   2000x2194
#   qa-report            2000x1403   2000x1434
#   social-preview       1280x640    1280x640
#   two-plugins          2000x1358   2000x1366
# Widths match. Heights run 8-40px taller than the committed files: the layout is the same, but
# the committed PNGs were trimmed a little tighter at the bottom, which was not recorded.
# So a re-render comes out a little taller than the picture in the repository: check the result
# against the committed one before committing it.
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
    arrows-before-after) width=1560; height="";   scale=1 ;;
    *)                   width=1400; height="";   scale=$(awk 'BEGIN{printf "%.6f", 2000/1400}') ;;
  esac

  if [ -z "$height" ]; then
    # Measure: a throwaway copy that writes the document height into <title>, then dump the DOM.
    local probe="$DIR/.probe-$name.html"
    { cat "$html"; echo '<script>document.title="H="+Math.ceil(document.body.getBoundingClientRect().height)</script>'; } > "$probe"
    height="$("$CHROME_BIN" --headless=new --disable-gpu --hide-scrollbars \
                --window-size="$width,2000" --virtual-time-budget=2000 --dump-dom \
                "file://$probe" 2>/dev/null | sed -n 's/.*<title>H=\([0-9]*\)<\/title>.*/\1/p' | head -1)"
    rm -f "$probe"
    if [ -z "$height" ]; then echo "render-images: could not measure $name" >&2; return 1; fi
  fi

  "$CHROME_BIN" --headless=new --disable-gpu --hide-scrollbars \
    --force-device-scale-factor="$scale" --window-size="$width,$height" \
    --screenshot="$png" "file://$html" >/dev/null 2>&1

  if [ "${QUANTIZE:-0}" = "1" ]; then
    if command -v pngquant >/dev/null 2>&1; then
      pngquant --force --ext .png 256 "$png"
    else
      echo "render-images: QUANTIZE=1 but pngquant is not installed; left $name as RGB" >&2
    fi
  fi

  if command -v sips >/dev/null 2>&1; then
    local w h
    w="$(sips -g pixelWidth "$png" | awk '/pixelWidth/{print $2}')"
    h="$(sips -g pixelHeight "$png" | awk '/pixelHeight/{print $2}')"
    echo "rendered $name.png ${w}x${h}"
  else
    echo "rendered $name.png (no sips here, size not reported)"
  fi
}

for n in "${names[@]}"; do render "$n"; done
