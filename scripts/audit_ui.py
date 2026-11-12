#!/usr/bin/env python3
"""
Scan a user's front-end code for UI that could become stretchy morph UI.

Usage:
  python audit_ui.py PATH [PATH ...] [--json] [--max-hits 6]

PATH can be files or directories. Prints, per UI category: how many hits, where (file:line and a
snippet), which showcase component and stretch technique it maps to. Also reports the stack
(framework, styling, existing animation libraries, reduced-motion handling).

This is a heuristic first pass. Read the code around every hit before proposing anything:
a "modal" class name may be dead CSS, a "tooltip" may be a native title attribute, etc.
"""
import argparse
import json
import os
import re
import signal
import sys
from pathlib import Path

SKIP_DIRS = {"node_modules", ".git", "dist", "build", ".next", ".nuxt", ".svelte-kit", "out",
             "coverage", "vendor", ".cache", ".turbo", ".vercel", "__pycache__", ".output", "public/build"}
EXTS = {".html", ".htm", ".jsx", ".tsx", ".js", ".ts", ".mjs", ".vue", ".svelte", ".astro",
        ".css", ".scss", ".sass", ".less", ".erb", ".php", ".twig", ".hbs", ".njk", ".liquid"}
MAX_FILE_BYTES = 600_000

A = r'["\']'  # attribute quote

# category: (label, showcase #, technique, morph idea, [regexes])
CATEGORIES = {
    "tabs": ("Tabs / tab bar", "#2 tabs", "edge pair",
             "indicator stretches like a worm between tabs",
             [rf'role={A}tab(list)?{A}', r'<Tabs?(List|Trigger)?\b', r'\b(TabList|TabPanel|TabsList|TabsTrigger)\b',
              rf'class(Name)?={A}[^"\']*\b(tabs?|nav-tabs|tab-bar)\b']),
    "segmented": ("Segmented control / button group", "#2 tabs (segmented)", "edge pair",
                  "selected pill worms between options",
                  [r'segmented', r'\bToggleGroup\b', r'\bbtn-group\b', r'\bButtonGroup\b']),
    "switch": ("Toggle switch", "#7 toggles", "edge pair + thinning knob",
               "knob stretches into a capsule while it travels",
               [rf'role={A}switch{A}', r'<Switch\b', rf'class(Name)?={A}[^"\']*\b(toggle|switch)\b']),
    "checkbox_radio": ("Checkboxes / radio groups", "#8 radio and checkbox", "edge pair (radio dot) + kick",
                       "radio dot flows between options; checkbox squashes on tick",
                       [rf'type={A}(checkbox|radio){A}', r'<(Checkbox|Radio|RadioGroup)\b', rf'role={A}radiogroup{A}']),
    "loading_button": ("Buttons with loading / submit states", "#6 send button", "split axes + volume + sequenced morph",
                       "button squeezes into a spinner circle, then a check, then back",
                       [r'\b(isLoading|isSubmitting|isPending|submitting|loading)\b\s*(\?|&&|\|\|)', r'<(Spinner|Loader|CircularProgress)\b',
                        r'aria-busy', r'disabled=\{\s*(isLoading|loading|isSubmitting|pending|isPending)']),
    "modal": ("Modals / dialogs", "#17 modal", "container transform",
              "the trigger button grows into the dialog and shrinks back on close",
              [r'<dialog\b', rf'role={A}(alert)?dialog{A}', r'<(Modal|Dialog|AlertDialog|DialogContent)\b', r'\.showModal\(',
               rf'class(Name)?={A}[^"\']*\bmodal\b']),
    "dropdown": ("Dropdowns / selects / menus / popovers", "#11 dropdown", "split axes + vertical edge-pair highlight",
                 "menu pours out of its button; highlight worms through options",
                 [r'<select\b', r'<(Select|Menu|DropdownMenu|Listbox|Combobox|Popover|MenuItems)\b', rf'role={A}(listbox|menu){A}',
                  rf'class(Name)?={A}[^"\']*\bdropdown\b']),
    "accordion": ("Accordions / collapsibles / details", "#22 accordion", "overshooting height + lagging content (makeAccordion for plain/CMS <details>)",
                  "panel overshoots its height, content lags like it is shaken, opened card drifts apart",
                  [r'<details\b', r'<(Accordion|Collapsible|Disclosure|Collapse)\b', r'\baccordion\b']),
    "carousel": ("Carousels / sliders of cards", "#5 carousel", "velocity skew + rubber band + worm dots",
                 "cards lean with swipe speed, edges resist like rubber",
                 [r'<(Swiper|SwiperSlide|Carousel|Slider|Slide)\b', r'scroll-snap-type', r'\bcarousel\b', r'\bswiper\b', r'embla|keen-slider|slick']),
    "range_slider": ("Range inputs / sliders", "#12 slider", "velocity stretch + lagging bubble",
                     "thumb stretches with drag speed, value bubble swings",
                     [rf'type={A}range{A}', rf'role={A}slider{A}']),
    "toast": ("Toasts / snackbars / alerts", "#18 toast", "split axes from a dot + stacked springs",
              "toast sprouts from a dot into a bar, old ones are pushed up",
              [r'\btoast\b', r'<(Toast|Toaster|Snackbar|Alert)\b', r'notistack|sonner|react-hot-toast|react-toastify|vue-toastification']),
    "tooltip": ("Tooltips", "#19 tooltip", "travelling follower + velocity stretch",
                "one tooltip travels between controls and resizes to its label",
                [r'<Tooltip\b', rf'role={A}tooltip{A}', r'data-tooltip', r'\btippy\b', r'\btooltip\b']),
    "sidebar": ("Sidebars / drawers / off-canvas", "#4 sidebar", "bulging SVG edge + vertical worm",
                "edge bulges with speed and wobbles flat; nav highlight worms",
                [r'<(Sidebar|Drawer|Sheet|SheetContent|Offcanvas)\b', r'<aside\b', r'\b(sidebar|drawer|offcanvas|side-nav)\b']),
    "bottom_sheet": ("Bottom sheets", "#20 bottom sheet", "bulging top edge + drag with velocity",
                     "draggable sheet whose top edge bends with speed",
                     [r'bottom-?sheet', r'BottomSheet', rf'side={A}bottom{A}', r'vaul']),
    "stepper": ("Steppers / wizards / progress steps", "#3 stepper", "edge pair blob + overshooting fill",
                "current-step blob stretches to the next step, progress line overshoots",
                [r'<(Stepper|Steps|Step|Wizard)\b', r'\bstepper\b', r'\b(currentStep|activeStep|stepIndex)\b', r'\[\s*step\s*,\s*setStep\s*\]', r'\bset(Current|Active)?Step\b']),
    "rating": ("Star ratings", "#14 rating", "edge-pair capsule + staggered kicks",
               "capsule behind the stars follows the pointer; stars pop in sequence",
               [r'<Rating\b', r'\brating\b', r'\bstar-?rating\b']),
    "chips": ("Chips / tags / filter pills", "#9 chips (multi) / #24 choice chips (single)", "springing icon slot + kick; 2-D edge-pair blob if single-select",
              "selected chip swells as its check pushes in; single-select: one capsule worms between chips, across rows",
              [r'<(Chip|Tag|FilterChip)\b', r'\b(chip|filter-chip)s?\b']),
    "search": ("Search fields", "#10 search", "split axes from icon + volume",
               "search icon bursts open into a field; suggestions bounce in",
               [rf'type={A}search{A}', rf'role={A}search{A}', rf'placeholder={A}[^"\']*(search|ค้นหา)']),
    "quantity": ("Quantity steppers / number inputs", "#13 quantity", "directional kick + digit roll",
                 "pill stretches toward the side pressed, digits roll",
                 [r'\b(quantity|qty)\b', rf'type={A}number{A}']),
    "add_to_cart": ("Add-to-cart / save / send-to actions", "#15 add to cart", "thrown clone + sequenced button morph",
                    "the product picture flies into the cart, button morphs into a stepper",
                    [r'add\s*to\s*cart|addToCart|add-to-cart|เพิ่มลงตะกร้า', r'\bcart\b', r'wishlist|addToWishlist']),
    "date_picker": ("Date pickers / calendars", "#23 date picker", "2-D edge-pair blob + per-row range capsules",
                    "selection blob flows between days; range pours row by row",
                    [rf'type={A}(date|datetime-local|month|week){A}', r'<(DatePicker|Calendar|DateRangePicker|DayPicker)\b',
                     r'datepicker|flatpickr|react-datepicker|react-day-picker|vuepic|pikaday']),
    "pagination": ("Pagination / page dots", "#5 carousel dots", "edge pair",
                   "current-page marker worms between numbers or dots",
                   [r'<Pagination\b', r'\bpagination\b', rf'aria-current={A}page{A}']),
    "badge": ("Badges / counters", "#15 cart badge", "kick on change",
              "count pops when it changes",
              [r'<Badge\b', r'\bbadge\b']),
    "fab": ("Floating action buttons", "#21 FAB", "split axes (width leads, then height)",
            "round button spreads into a form or menu",
            [r'\bfab\b', r'floating-action', r'<Fab\b', r'SpeedDial']),
    "menu_toggle": ("Hamburger / nav toggles", "new-components: hamburger", "edge pair bars + container transform",
                    "bars fold into an X and the button grows into the menu",
                    [r'hamburger|menu-toggle|navbar-toggler|nav-toggle', rf'aria-label={A}(open |toggle )?(menu|navigation){A}']),
    "reorder": ("Drag-to-reorder lists", "new-components: drag to reorder", "pointer follower + tilt + FLIP",
                "picked item tilts with speed while others spring apart",
                [r'react-beautiful-dnd|@hello-pangea/dnd|@dnd-kit|sortablejs|vuedraggable|svelte-dnd', r'\bdraggable\b']),
    "like": ("Like / favourite buttons", "new-components: like button", "kick squash + ring pulse",
             "heart squashes on press and launches on release",
             [r'\b(isLiked|liked|toggleLike|likeCount|onLike|LikeButton|isFavou?rite|toggleFavou?rite)\b', r'HeartIcon|icon-heart|bi-heart|fa-heart']),
}

STACK_SIGNS = {
    "react": [r'from\s+["\']react["\']', r'\buseState\b', r'\.jsx\b'],
    "vue": [r'<template\b', r'from\s+["\']vue["\']', r'defineComponent'],
    "svelte": [r'<script[^>]*>\s*(export let|import)', r'\$:\s'],
    "angular": [r'@Component\(', r'from\s+["\']@angular'],
    "tailwind": [r'class(Name)?=["\'][^"\']*\b(px-\d|py-\d|bg-[a-z]+-\d{2,3}|text-[a-z]+-\d{2,3}|rounded-(md|lg|xl|2xl|full))\b'],
    "framer-motion / motion": [r'framer-motion', r'from\s+["\']motion', r'<motion\.'],
    "react-spring": [r'@react-spring|react-spring'],
    "gsap": [r'\bgsap\b'],
    "anime.js / popmotion": [r'animejs|popmotion'],
    "radix / shadcn": [r'@radix-ui', r'components/ui/'],
    "headless ui": [r'@headlessui'],
    "mui / chakra / antd": [r'@mui/|@chakra-ui|antd'],
}
MOTION_SIGNS = {
    "css transitions": r'transition\s*:|transition-(all|colors|transform|opacity)\b',
    "css keyframes": r'@keyframes',
    "reduced-motion handling": r'prefers-reduced-motion|useReducedMotion|motion-reduce|motion-safe',
}


def iter_files(paths):
    for p in paths:
        p = Path(p)
        if p.is_file():
            yield p
        elif p.is_dir():
            for root, dirs, files in os.walk(p):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith('.')]
                for f in files:
                    fp = Path(root) / f
                    if fp.suffix.lower() in EXTS:
                        yield fp
                    elif f == "package.json":
                        yield fp


def main():
    # Windows consoles default to a legacy code page that garbles Thai snippets.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--max-hits", type=int, default=6)
    args = ap.parse_args()

    compiled = {k: [re.compile(rx, re.I) for rx in v[4]] for k, v in CATEGORIES.items()}
    hits = {k: [] for k in CATEGORIES}
    stack, motion = {}, {k: 0 for k in MOTION_SIGNS}
    deps = {}
    nfiles = 0

    for fp in iter_files(args.paths):
        try:
            if fp.stat().st_size > MAX_FILE_BYTES:
                continue
            text = fp.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        nfiles += 1
        if fp.name == "package.json":
            try:
                pj = json.loads(text)
                for sec in ("dependencies", "devDependencies"):
                    deps.update(pj.get(sec, {}) or {})
            except ValueError:
                pass
            continue
        if fp.suffix in (".jsx", ".tsx"):
            stack["react"] = stack.get("react", 0) + 1
        if fp.suffix == ".vue":
            stack["vue"] = stack.get("vue", 0) + 1
        if fp.suffix == ".svelte":
            stack["svelte"] = stack.get("svelte", 0) + 1
        for name, rxs in STACK_SIGNS.items():
            if any(re.search(rx, text) for rx in rxs):
                stack[name] = stack.get(name, 0) + 1
        for name, rx in MOTION_SIGNS.items():
            motion[name] += len(re.findall(rx, text, re.I))
        lines = text.splitlines()
        for i, line in enumerate(lines, 1):
            if len(line) > 600:
                line = line[:600]
            for cat, rxs in compiled.items():
                if any(rx.search(line) for rx in rxs):
                    hits[cat].append({"file": str(fp), "line": i, "snippet": line.strip()[:110]})

    for d in deps:
        for key, label in (("react", "react"), ("vue", "vue"), ("svelte", "svelte"), ("tailwindcss", "tailwind"),
                           ("framer-motion", "framer-motion / motion"), ("motion", "framer-motion / motion"),
                           ("@react-spring/web", "react-spring"), ("gsap", "gsap")):
            if d == key:
                stack[label] = stack.get(label, 0) + 1

    found = {k: v for k, v in hits.items() if v}
    result = {
        "files_scanned": nfiles,
        "stack": sorted(stack, key=lambda k: -stack[k]),
        "motion": motion,
        "candidates": [
            {"category": k, "label": CATEGORIES[k][0], "showcase": CATEGORIES[k][1], "technique": CATEGORIES[k][2],
             "idea": CATEGORIES[k][3], "count": len(v),
             "files": sorted({h["file"] for h in v}), "hits": v[:args.max_hits]}
            for k, v in sorted(found.items(), key=lambda kv: -len(kv[1]))
        ],
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(f"Scanned {nfiles} files")
    print("Stack:", ", ".join(result["stack"]) or "plain HTML/CSS/JS (no framework detected)")
    print("Motion today:", ", ".join(f"{k} {v}" for k, v in motion.items()))
    if motion["reduced-motion handling"] == 0:
        print("  note: no prefers-reduced-motion handling found")
    if not result["candidates"]:
        print("\nNo UI candidates found. Check the paths, or the UI may be rendered from a template or CMS.")
        return
    print("\nCandidates (heuristic; read the code before proposing):")
    for c in result["candidates"]:
        print(f"\n## {c['label']}  [{c['count']} hits in {len(c['files'])} file(s)]")
        print(f"   becomes: {c['idea']}")
        print(f"   technique: {c['technique']}   reference: showcase {c['showcase']}")
        for h in c["hits"]:
            print(f"   - {h['file']}:{h['line']}  {h['snippet']}")
        if c["count"] > len(c["hits"]):
            print(f"   … {c['count'] - len(c['hits'])} more")


if __name__ == "__main__":
    if hasattr(signal, "SIGPIPE"):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)  # quiet when piped into head
    main()
