#!/usr/bin/env python3
"""
Smoke-test a stretchy UI page in headless Chromium and capture animation frames.

Usage:
  python check_page.py PAGE.html [--out DIR] [--frames "CLICK_SELECTOR[@CLIP_SELECTOR]" ...]
                                  [--count 8] [--interval 110] [--widths 1280,390]
                                  [--jumps SELECTOR ...] [--no-jumps] [--slowmo 4]

What it reports, for each viewport width:
  * JavaScript errors and console errors (failed web-font loads are expected offline)
  * horizontal overflow (page wider than the viewport) and the outermost offending elements
  * visible controls whose centre is covered by another element, with that element's opacity
    (an opacity-0 blocker is the classic "invisible layer steals the click" bug)
It saves a full-page screenshot per width.

Jump strips (first width, on by default): for every group of selection controls (a tablist, a
radiogroup, or the parent of [role=tab] / [role=radio] buttons) it selects the first item, clicks
the last one in slow motion, and saves jump_N.png: the group's box, one full-size frame per row.
A long jump is where indicator bugs show. LOOK at every strip; the script cannot judge them:
  * the clicked item must stay readable in every frame (a label that turns white, or a surface
    that goes transparent, before the indicator arrives makes the item vanish mid-flight);
  * the indicator must pass over the items it crosses (under their labels only), not hide behind
    their surfaces and show only in the gaps.
Add selectors with --jumps (elements inside one parent form a group), skip with --no-jumps.

--frames clicks CLICK_SELECTOR, then saves COUNT screenshots INTERVAL ms apart, cropped to
CLIP_SELECTOR (or the clicked element's closest .stage, or the viewport), and stitches them into
a contact sheet so you can judge the motion frame by frame. Repeat --frames for several.

--slowmo K (default 4) runs the page's clock K times slower while frames and jump strips are
captured: performance.now, requestAnimationFrame timestamps, setTimeout/setInterval delays and
CSS animations/transitions all slow down. A screenshot takes 100-200 ms, so at full speed a
spring is nearly settled by the second frame; slowed, each frame covers a short slice of motion.
--slowmo 1 turns it off.

Exit code 1 if errors, overflow or click blockers were found. Frames and jump strips are for
your eyes and never change the exit code.
"""
import argparse
import pathlib
import sys
import time

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


def capture_frames(page, spec, out_dir, idx, count, interval, slowmo=1):
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
    with SlowMo(page, slowmo):
        target.click()
        for i in range(1, count):
            page.wait_for_timeout(interval)
            p = out_dir / f"frames{idx}_{i:02d}.png"
            page.screenshot(path=str(p), clip=clip)
            paths.append(p)
    page.wait_for_timeout(500)                              # let it settle at full speed
    contact_sheet(paths, out_dir / f"frames{idx}_sheet.png")


SLOWMO_INIT = r"""(() => {
  const pn = performance.now.bind(performance);
  let k = 1, baseReal = pn(), baseVirt = baseReal;
  const now = () => baseVirt + (pn() - baseReal) / k;
  window.__setSlowmo = x => { baseVirt = now(); baseReal = pn(); k = x; };
  performance.now = now;
  const raf = window.requestAnimationFrame.bind(window);
  window.requestAnimationFrame = cb => raf(() => cb(now()));
  const st = window.setTimeout.bind(window), si = window.setInterval.bind(window);
  window.setTimeout = (f, d = 0, ...a) => st(f, d * k, ...a);
  window.setInterval = (f, d = 0, ...a) => si(f, d * k, ...a);
})();"""


class SlowMo:
    """Slow the page clock and CSS animations by k inside a with-block."""
    def __init__(self, page, k):
        self.page, self.k = page, k
        self.cdp = None
        if k != 1:
            try:
                self.cdp = page.context.new_cdp_session(page)
                self.cdp.send("Animation.enable")
            except Exception:
                self.cdp = None                             # not Chromium: JS clock only

    def __enter__(self):
        if self.k != 1:
            self.page.evaluate(f"window.__setSlowmo && window.__setSlowmo({self.k})")
            if self.cdp:
                self.cdp.send("Animation.setPlaybackRate", {"playbackRate": 1 / self.k})
        return self

    def __exit__(self, *exc):
        if self.k != 1:
            self.page.evaluate("window.__setSlowmo && window.__setSlowmo(1)")
            if self.cdp:
                self.cdp.send("Animation.setPlaybackRate", {"playbackRate": 1})


JUMP_DEFAULT = '[role="tab"], button[role="radio"], [role="radio"]:not(input)'
LIST_GROUPS_JS = r"""(sel) => {
  // Group visible controls by tablist / radiogroup, else by parent; tag each group's box, first and last.
  const groups = new Map();
  for (const e of document.querySelectorAll(sel)) {
    if (e.closest('[inert]') || e.disabled) continue;
    const r = e.getBoundingClientRect(), cs = getComputedStyle(e);
    if (r.width < 8 || r.height < 8 || cs.visibility === 'hidden' || cs.display === 'none') continue;
    const g = e.closest('[role=tablist],[role=radiogroup]') || e.parentElement;
    if (!groups.has(g)) groups.set(g, []);
    groups.get(g).push(e);
  }
  let n = 0;
  for (const [g, list] of groups) {
    if (list.length < 2) continue;
    g.setAttribute('data-jump-group', n);
    list[0].setAttribute('data-jump-first', n);
    list[list.length - 1].setAttribute('data-jump-last', n);
    n++;
  }
  return n;
}"""


def stack_strip(pngs, out_path, gap=4):
    from PIL import Image
    import io
    ims = [Image.open(io.BytesIO(b)).convert("RGB") for b in pngs]
    w = max(i.width for i in ims)
    sheet = Image.new("RGB", (w, sum(i.height for i in ims) + gap * (len(ims) - 1)), (128, 128, 128))
    y = 0
    for im in ims:
        sheet.paste(im, (0, y))
        y += im.height + gap
    sheet.save(out_path)


def capture_jumps(page, selector, out_dir, slowmo=4, count=10, limit=12):
    try:
        import PIL  # noqa: F401
    except ImportError:
        print("  (Pillow not installed; jump strips skipped)")
        return []
    n = min(page.evaluate(LIST_GROUPS_JS, selector), limit)
    saved = []
    for g in range(n):
        try:
            group = page.locator(f'[data-jump-group="{g}"]')
            group.scroll_into_view_if_needed()
            page.locator(f'[data-jump-first="{g}"]').click()
            page.wait_for_timeout(900)                      # settle on the first item
            box = group.bounding_box()
            pad = 12
            vp = page.viewport_size
            clip = {"x": max(0, box["x"] - pad), "y": max(0, box["y"] - pad)}
            clip["width"] = min(box["width"] + 2 * pad, vp["width"] - clip["x"])
            clip["height"] = min(box["height"] + 2 * pad, vp["height"] - clip["y"])
            pngs = [page.screenshot(clip=clip)]
            with SlowMo(page, slowmo):
                page.locator(f'[data-jump-last="{g}"]').click()
                for _ in range(count - 1):
                    pngs.append(page.screenshot(clip=clip))
            page.wait_for_timeout(500)
            pngs.append(page.screenshot(clip=clip))         # settled, full speed
            out = out_dir / f"jump_{g}.png"
            stack_strip(pngs, out)
            label = group.evaluate("e => e.getAttribute('aria-label') || (e.id ? '#' + e.id : e.className && '.' + String(e.className).split(' ')[0]) || e.tagName.toLowerCase()")
            saved.append(f"{label}: {out}")
        except Exception as e:                              # keep going with the other groups
            saved.append(f"group {g}: could not capture ({e.__class__.__name__})")
    page.evaluate("document.querySelectorAll('[data-jump-group],[data-jump-first],[data-jump-last]').forEach(e => "
                  "['data-jump-group','data-jump-first','data-jump-last'].forEach(a => e.removeAttribute(a)))")
    return saved


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("page")
    ap.add_argument("--out", default="check-output")
    ap.add_argument("--frames", action="append", default=[])
    ap.add_argument("--count", type=int, default=8)
    ap.add_argument("--interval", type=int, default=110)
    ap.add_argument("--widths", default="1280,390")
    ap.add_argument("--jumps", action="append", default=[],
                    help="extra selector for selection controls to capture first-to-last jump strips of")
    ap.add_argument("--no-jumps", action="store_true", help="skip the jump strips")
    ap.add_argument("--slowmo", type=float, default=4,
                    help="slow the page clock this many times while capturing frames and jump strips (1 = off)")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):                  # Thai labels on Windows consoles
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    page_path = pathlib.Path(args.page).resolve()
    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    problems = 0

    with sync_playwright() as p:
        browser = p.chromium.launch()
        for width in [int(w) for w in args.widths.split(",")]:
            print(f"\n== {width}px ==")
            page = browser.new_page(viewport={"width": width, "height": 900 if width > 600 else 844})
            if args.slowmo != 1:
                page.add_init_script(SLOWMO_INIT)
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
                        capture_frames(page, spec, out_dir, i, args.count, args.interval, args.slowmo)
                    except Exception as e:  # keep checking the rest
                        print(f"    could not capture: {e}")

            if width == int(args.widths.split(",")[0]) and not args.no_jumps:
                strips = capture_jumps(page, ", ".join([JUMP_DEFAULT] + args.jumps), out_dir, args.slowmo)
                if strips:
                    print("  jump strips (look at the clicked item in every row):")
                    for s in strips:
                        print(f"    {s}")

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
