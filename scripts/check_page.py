#!/usr/bin/env python3
"""
Smoke-test a stretchy UI page in headless Chromium and capture animation frames.

Usage:
  python check_page.py PAGE.html [--out DIR] [--frames "CLICK_SELECTOR[@CLIP_SELECTOR]" ...]
                                  [--count 8] [--interval 110] [--widths 1280,390]

What it reports, for each viewport width:
  * JavaScript errors and console errors (failed web-font loads are expected offline)
  * horizontal overflow (page wider than the viewport) and the outermost offending elements
  * visible controls whose centre is covered by another element, with that element's opacity
    (an opacity-0 blocker is the classic "invisible layer steals the click" bug)
It saves a full-page screenshot per width.

--frames clicks CLICK_SELECTOR, then saves COUNT screenshots INTERVAL ms apart, cropped to
CLIP_SELECTOR (or the clicked element's closest .stage, or the viewport), and stitches them into
a contact sheet so you can judge the motion frame by frame. Repeat --frames for several.

Exit code 1 if errors, overflow or click blockers were found.
"""
import argparse
import pathlib
import sys

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Playwright is not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(2)

BLOCKERS_JS = r"""() => {
  const opacityChain = e => { let o = 1; while (e && e.nodeType === 1) { o *= parseFloat(getComputedStyle(e).opacity); e = e.parentElement; } return o; };
  const name = e => e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') +
    (typeof e.className === 'string' && e.className.trim() ? '.' + e.className.trim().split(/\s+/).join('.') : '');
  const sel = 'button,a[href],input,select,textarea,[role=button],[role=tab],[role=switch],[role=slider],[role=radio],[role=option],[role=menuitem]';
  const out = [];
  for (const b of document.querySelectorAll(sel)) {
    if (b.closest('[inert]')) continue;
    const r = b.getBoundingClientRect(); if (r.width < 4 || r.height < 4) continue;
    const cs = getComputedStyle(b); if (cs.visibility === 'hidden' || cs.display === 'none' || cs.pointerEvents === 'none') continue;
    if (opacityChain(b) < 0.05) continue;
    const x = r.left + r.width / 2, y = r.top + r.height / 2;
    if (x < 0 || y < 0 || x > innerWidth || y > innerHeight) continue;
    const t = document.elementFromPoint(x, y);
    if (!t || b.contains(t) || t.contains(b)) continue;
    // ignore labels wrapping their own input
    if (t.closest('label') && t.closest('label').contains(b)) continue;
    out.push({ control: name(b), blocker: name(t), blockerOpacity: +opacityChain(t).toFixed(2) });
  }
  return out;
}"""

OVERFLOW_JS = r"""() => {
  const W = document.documentElement.clientWidth;
  if (document.documentElement.scrollWidth <= W + 1) return { scrollWidth: document.documentElement.scrollWidth, offenders: [] };
  const clipped = e => { for (let p = e.parentElement; p; p = p.parentElement) { const o = getComputedStyle(p).overflowX; if (o === 'hidden' || o === 'clip' || o === 'auto' || o === 'scroll') return true; } return false; };
  const bad = [...document.body.querySelectorAll('*')].filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.right > W + 1 && !clipped(e); });
  const outer = bad.filter(e => !bad.includes(e.parentElement));
  const name = e => e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + (typeof e.className === 'string' && e.className.trim() ? '.' + e.className.trim().split(/\s+/).join('.') : '');
  return { scrollWidth: document.documentElement.scrollWidth, offenders: outer.slice(0, 8).map(e => name(e) + ' right=' + Math.round(e.getBoundingClientRect().right)) };
}"""


def scan_blockers(page):
    found, seen = [], set()
    height = page.evaluate("document.documentElement.scrollHeight")
    vh = page.evaluate("innerHeight")
    y = 0
    while y < height:
        page.evaluate(f"window.scrollTo(0,{y})")
        page.wait_for_timeout(60)
        for item in page.evaluate(BLOCKERS_JS):
            key = (item["control"], item["blocker"])
            if key not in seen:
                seen.add(key)
                found.append(item)
        y += vh
    page.evaluate("window.scrollTo(0,0)")
    return found


def contact_sheet(paths, out_path, cols=2, scale=0.5):
    try:
        from PIL import Image
    except ImportError:
        print("  (Pillow not installed; frames saved individually)")
        return
    ims = [Image.open(p) for p in paths]
    w, h = ims[0].size
    tw, th = max(1, int(w * scale)), max(1, int(h * scale))
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (tw * cols, th * rows), "white")
    for i, im in enumerate(ims):
        sheet.paste(im.resize((tw, th)), ((i % cols) * tw, (i // cols) * th))
    sheet.save(out_path)
    print(f"  contact sheet: {out_path}")


def capture_frames(page, spec, out_dir, idx, count, interval):
    click_sel, _, clip_sel = spec.partition("@")
    target = page.locator(click_sel).first
    target.scroll_into_view_if_needed()
    page.wait_for_timeout(250)
    if clip_sel:
        box = page.locator(clip_sel).first.bounding_box()
    else:
        box = target.evaluate("e => { const s = e.closest('.stage') || document.documentElement; const r = s.getBoundingClientRect(); return {x:r.left,y:r.top,width:r.width,height:r.height}; }")
    vp = page.viewport_size
    clip = {"x": max(0, box["x"]), "y": max(0, box["y"]),
            "width": min(box["width"], vp["width"]), "height": min(box["height"], vp["height"])}
    paths = []
    first = out_dir / f"frames{idx}_00.png"
    page.screenshot(path=str(first), clip=clip)
    paths.append(first)
    target.click()
    for i in range(1, count):
        page.wait_for_timeout(interval)
        p = out_dir / f"frames{idx}_{i:02d}.png"
        page.screenshot(path=str(p), clip=clip)
        paths.append(p)
    contact_sheet(paths, out_dir / f"frames{idx}_sheet.png")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("page")
    ap.add_argument("--out", default="check-output")
    ap.add_argument("--frames", action="append", default=[])
    ap.add_argument("--count", type=int, default=8)
    ap.add_argument("--interval", type=int, default=110)
    ap.add_argument("--widths", default="1280,390")
    args = ap.parse_args()

    page_path = pathlib.Path(args.page).resolve()
    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    problems = 0

    with sync_playwright() as p:
        browser = p.chromium.launch()
        for width in [int(w) for w in args.widths.split(",")]:
            print(f"\n== {width}px ==")
            page = browser.new_page(viewport={"width": width, "height": 900 if width > 600 else 844})
            errors = []
            page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
            page.on("console", lambda m: errors.append(f"console: {m.text}") if m.type == "error" else None)
            page.goto(page_path.as_uri())
            page.wait_for_timeout(1200)

            ov = page.evaluate(OVERFLOW_JS)
            if ov["offenders"]:
                problems += 1
                print(f"  OVERFLOW: page is {ov['scrollWidth']}px wide")
                for o in ov["offenders"]:
                    print(f"    {o}")
            else:
                print("  no horizontal overflow")

            blockers = scan_blockers(page)
            if blockers:
                problems += 1
                print("  CLICK BLOCKERS:")
                for b in blockers:
                    flag = "  <- invisible layer" if b["blockerOpacity"] < 0.05 else ""
                    print(f"    {b['control']} covered by {b['blocker']} (opacity {b['blockerOpacity']}){flag}")
            else:
                print("  no click blockers")

            shot = out_dir / f"page_{width}.png"
            page.screenshot(path=str(shot), full_page=True)
            print(f"  screenshot: {shot}")

            if width == int(args.widths.split(",")[0]):
                for i, spec in enumerate(args.frames):
                    print(f"  frames for {spec}")
                    try:
                        capture_frames(page, spec, out_dir, i, args.count, args.interval)
                    except Exception as e:  # keep checking the rest
                        print(f"    could not capture: {e}")

            real = [e for e in errors if "ERR_NAME_NOT_RESOLVED" not in e and "Failed to load resource" not in e]
            if real:
                problems += 1
                print("  JS ERRORS:")
                for e in real:
                    print(f"    {e}")
            else:
                print("  no JS errors" + (" (font requests failed offline, ignored)" if errors else ""))
            page.close()
        browser.close()

    print("\nRESULT:", "problems found" if problems else "clean")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
