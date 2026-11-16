#!/usr/bin/env python3
"""
Scan a user's front-end code for UI that could become stretchy morph UI.

Usage:
  python audit_ui.py PATH [PATH ...] [--json] [--max-hits 6]

PATH can be files or directories. The text report shows the file count, the stack (framework,
styling, animation libraries, an existing copy of the stretchy core), the motion already in use,
the shared JSX components with their use counts, and per UI category the hits as file:line
(d = definition line), the showcase component and the stretch technique it maps to.
CSS-only matches are reported on one line. --json prints the same data as compact JSON.
Block comments, comment-only lines and copies of the stretchy core (a core .js file, or the CORE block
of a page built from the starter) are not scanned as UI.

This is a heuristic first pass. Read the code around every hit before proposing anything:
a "modal" class name may be dead CSS, a "tooltip" may be a native title attribute, etc.
"""
import argparse
import collections
import json
import os
import re
import signal
import sys
from pathlib import Path

SKIP_DIRS = {"node_modules", ".git", "dist", "build", ".next", ".nuxt", ".svelte-kit", "out",
             "coverage", "vendor", ".cache", ".turbo", ".vercel", "__pycache__", ".output"}
# Skipped, and their candidate files are counted as skipped.
COUNTED_SKIP_DIRS = {"__tests__", "__mocks__", "storybook-static", "test-results", "playwright-report"}
SKIP_NAME_PARTS = (".min.", ".test.", ".spec.", ".stories.", ".story.")
SKILL_DIR = Path(__file__).resolve().parent.parent
CSS_EXTS = {".css", ".scss", ".sass", ".less"}
JSX_EXTS = {".jsx", ".tsx", ".vue", ".svelte", ".astro"}
COMMENT_STARTS = ("//", "/*", "*/", "* ", "<!--", "{/*")
DEF_RX = re.compile(r'^\s*(export\s+)?(default\s+)?(async\s+)?(function|class|const)\s+[A-Z]\w*')
CORE_SIGN = "stretchy-core (already present)"
DEP_LABELS = (("react", "react"), ("vue", "vue"), ("svelte", "svelte"), ("tailwindcss", "tailwind"),
              ("framer-motion", "framer-motion / motion"), ("motion", "framer-motion / motion"),
              ("@react-spring/web", "react-spring"), ("gsap", "gsap"))

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

# One combined pattern per category: a whole-file search is a superset filter for the line tests.
COMPILED_CATS = {k: re.compile('|'.join('(?:%s)' % rx for rx in v[4]), re.I) for k, v in CATEGORIES.items()}
STACK_RX = {k: [re.compile(rx) for rx in v] for k, v in STACK_SIGNS.items()}
MOTION_RX = {k: re.compile(v, re.I) for k, v in MOTION_SIGNS.items()}


def within(path, base):
    a = os.path.normcase(str(path))
    b = os.path.normcase(str(base))
    try:
        return os.path.commonpath([a, b]) == b
    except ValueError:
        return False


def is_candidate(fp):
    return fp.suffix.lower() in EXTS or fp.name == "package.json"


def is_skipped_file(fp, allow_skill):
    name = fp.name.lower()
    if name.endswith(".d.ts") or any(part in name for part in SKIP_NAME_PARTS):
        return True
    return not allow_skill and within(fp, SKILL_DIR)


def iter_files(paths):
    """Yield (file, skipped) for each candidate file under the resolved input paths."""
    for p in paths:
        # The skill folder is skipped unless the command line names a folder inside it.
        allow_skill = within(p, SKILL_DIR) and p != SKILL_DIR
        if p.is_file():
            if is_candidate(p):
                yield p, is_skipped_file(p, allow_skill)
        elif p.is_dir():
            for root, dirs, files in os.walk(p):
                for d in dirs:
                    if d in COUNTED_SKIP_DIRS:
                        for sub_root, _, sub_files in os.walk(Path(root) / d):
                            for f in sub_files:
                                fp = Path(sub_root) / f
                                if is_candidate(fp):
                                    yield fp, True
                dirs[:] = [d for d in dirs
                           if d not in SKIP_DIRS and d not in COUNTED_SKIP_DIRS and not d.startswith(".")]
                for f in files:
                    fp = Path(root) / f
                    if is_candidate(fp):
                        yield fp, is_skipped_file(fp, allow_skill)


def plural(n, word):
    return "%d %s%s" % (n, word, "" if n == 1 else "s")


def select_hits(cat_hits, max_hits):
    """Group hits by file (definition files first, then most hits), keep the first max_hits.
    Returns (files, chosen, shown): chosen is [(file, hits)], shown is the flat list."""
    by_file = {}
    for h in cat_hits:
        by_file.setdefault(h["file"], []).append(h)
    files = sorted(by_file, key=lambda f: (not any(h["kind"] == "def" for h in by_file[f]),
                                           -len(by_file[f]), f))
    chosen, left = [], max_hits
    for f in files:
        if left <= 0:
            break
        take = by_file[f][:left]
        chosen.append((f, take))
        left -= len(take)
    shown = [h for _, take in chosen for h in take]
    return files, chosen, shown


COMMENT_RX = re.compile(r'\{/\*.*?\*/\}|/\*.*?\*/|<!--.*?-->', re.S)
LINE_COMMENT_RX = re.compile(r'(?m)^\s*//.*$')
CORE_BLOCK_RX = re.compile(r'(?ms)^/\* CORE START.*?^/\* CORE END \*/[^\r\n]*')


def is_core_copy(fp, text):
    """A stretchy-core.js copy inside the project (not user code)."""
    return fp.suffix.lower() in (".js", ".mjs", ".ts") and "stretchy-core.js" in text[:600] and "class Spring" in text


def blank_core_block(text):
    """Blank the inline core of a page built from the starter. Newlines are kept, so line numbers stay right."""
    return CORE_BLOCK_RX.sub(lambda m: "\n" * m.group(0).count("\n"), text)


def strip_comments(text):
    """Remove block, JSX and line comments before counting JSX tags."""
    return LINE_COMMENT_RX.sub('', COMMENT_RX.sub('', text))


def comment_closer(line):
    """The closer of a block comment that this line opens and does not close, else None."""
    closer = None
    for m in re.finditer(r'/\*|\*/|<!--|-->', line):
        tok = m.group(0)
        if closer is None:
            closer = {"/*": "*/", "<!--": "-->"}.get(tok)
        elif tok == closer:
            closer = None
    return closer


def main():
    # Windows consoles default to a legacy code page that garbles Thai snippets.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--max-hits", type=int, default=6)
    args = ap.parse_args()

    inputs = [Path(p).resolve() for p in args.paths]
    missing = [p for p, fp in zip(args.paths, inputs) if not fp.exists()]
    if missing:
        for p in missing:
            print(f"path not found: {p}")
        sys.exit(2)
    bases = [p if p.is_dir() else p.parent for p in inputs]
    try:
        root = Path(os.path.commonpath([str(b) for b in bases]))
    except ValueError:
        root = bases[0]
    root_posix = root.as_posix()

    def rel(fp):
        return os.path.relpath(str(fp), str(root)).replace(os.sep, "/")

    hits = {k: [] for k in CATEGORIES}
    css_count = collections.Counter()
    css_files = collections.defaultdict(set)
    css_first = {}
    stack = collections.Counter()
    motion = {k: 0 for k in MOTION_RX}
    uses = collections.Counter()
    use_files = collections.defaultdict(set)
    deps = {}
    nfiles = skipped = 0

    for fp, is_skip in iter_files(inputs):
        if is_skip:
            skipped += 1
            continue
        try:
            if fp.stat().st_size > MAX_FILE_BYTES:
                skipped += 1
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
            except (ValueError, AttributeError):
                pass
            continue

        name_rel = rel(fp)
        names = set()
        if fp.suffix in (".jsx", ".tsx"):
            names.add("react")
        if fp.suffix == ".vue":
            names.add("vue")
        if fp.suffix == ".svelte":
            names.add("svelte")
        names.update(n for n, rxs in STACK_RX.items() if any(rx.search(text) for rx in rxs))
        if "class Spring" in text and "edgePair" in text:
            names.add(CORE_SIGN)
        stack.update(names)
        if is_core_copy(fp, text):
            continue  # a copy of the core is not user code: no candidates, motion counts or shared components
        scan_text = blank_core_block(text)
        for n, rx in MOTION_RX.items():
            motion[n] += len(rx.findall(scan_text))
        if fp.suffix in JSX_EXTS:
            for n in re.findall(r'<([A-Z][A-Za-z0-9]*)', strip_comments(scan_text)):
                uses[n] += 1
                use_files[n].add(name_rel)

        active = [k for k, rx in COMPILED_CATS.items() if rx.search(scan_text)]
        if not active:
            continue
        css_file = fp.suffix.lower() in CSS_EXTS
        in_style = False
        block_end = None  # closer of a multi-line comment that is still open
        for i, raw in enumerate(scan_text.splitlines(), 1):
            if css_file:
                css = True
            else:
                css = in_style or "<style" in raw
                if "<style" in raw:
                    in_style = True
                if "</style>" in raw:
                    in_style = False
            if block_end is not None:
                if block_end in raw:
                    block_end = None
                continue
            block_end = comment_closer(raw)
            if block_end is not None:
                continue
            line = raw[:600]
            if css:
                for k in active:
                    if COMPILED_CATS[k].search(line):
                        css_count[k] += 1
                        css_files[k].add(name_rel)
                        css_first.setdefault(k, (name_rel, i))
                continue
            if line.lstrip().startswith(COMMENT_STARTS):
                continue
            kind = "def" if DEF_RX.search(line) else "use"
            for k in active:
                if COMPILED_CATS[k].search(line):
                    hits[k].append({"file": name_rel, "line": i, "kind": kind,
                                    "snippet": line.strip()[:110]})

    stack.update({label for d in deps for key, label in DEP_LABELS if d == key})
    stack_names = sorted(stack, key=lambda k: -stack[k])
    shared = [{"name": n, "uses": c, "files": len(use_files[n])}
              for n, c in sorted(uses.items(), key=lambda kv: (-kv[1], kv[0])) if c >= 2][:8]

    # Categories with non-CSS hits first (most hits first), CSS-only categories last.
    order = sorted((k for k in CATEGORIES if hits[k] or css_count[k]), key=lambda k: -len(hits[k]))
    candidates = []
    for k in order:
        label, showcase, technique, idea, _ = CATEGORIES[k]
        files, _, shown = select_hits(hits[k], args.max_hits)
        candidates.append({"category": k, "label": label, "showcase": showcase, "technique": technique,
                           "idea": idea, "count": len(hits[k]), "css_count": css_count[k],
                           "files": files, "hits": shown})

    if args.json:
        result = {"root": root_posix, "files_scanned": nfiles, "files_skipped": skipped,
                  "stack": stack_names, "motion": motion, "shared_components": shared,
                  "candidates": candidates}
        print(json.dumps(result, ensure_ascii=False, separators=(',', ':')))
        return

    print(f"Scanned {plural(nfiles, 'file')} under {root_posix} "
          f"(skipped {skipped}: tests, stories, minified, generated or the skill itself)")
    print("Stack: " + (", ".join(stack_names) or "plain HTML/CSS/JS (no framework detected)"))
    if CORE_SIGN in stack:
        print("Note: the stretchy core is already in this code: reuse it, do not add a second copy.")
    motion_txt = ", ".join(f"{k} {v}" for k, v in motion.items())
    if motion["reduced-motion handling"] == 0:
        motion_txt += " (none: add it)"
    print("Motion today: " + motion_txt)
    if shared:
        print("Shared components (uses/files): "
              + ", ".join(f"{s['name']} {s['uses']}/{s['files']}" for s in shared))
    if not candidates:
        print("\nNo UI candidates found. Check the paths, or the UI may be rendered from a template or CMS.")
        return
    print("\nCandidates (heuristic: read the code around each hit before proposing; d = definition line)\n")
    for c in candidates:
        k = c["category"]
        label, showcase, technique, idea, _ = CATEGORIES[k]
        if not hits[k]:
            first_file, first_line = css_first[k]
            print(f"{label}: CSS only, {plural(css_count[k], 'line')} in {plural(len(css_files[k]), 'file')} "
                  f"({first_file}:{first_line}) -> showcase {showcase} | check the class is still used")
            continue
        files, chosen, shown = select_hits(hits[k], args.max_hits)
        css_part = f" (+{css_count[k]} in CSS)" if css_count[k] else ""
        print(f"{label}: {plural(len(hits[k]), 'hit')}, {plural(len(files), 'file')}{css_part}"
              f" -> showcase {showcase} | {technique} | {idea}")
        for f, take in chosen:
            nums = ",".join(f"{h['line']}{'d' if h['kind'] == 'def' else ''}" for h in take)
            print(f"  {f}:{nums}  {take[0]['snippet'][:80]}")
        left = len(hits[k]) - len(shown)
        if left:
            more_files = len(files) - len(chosen)
            tail = f" in {more_files} more {'file' if more_files == 1 else 'files'}" if more_files else ""
            print(f"  … {left} more {'hit' if left == 1 else 'hits'}{tail}")


if __name__ == "__main__":
    if hasattr(signal, "SIGPIPE"):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)  # quiet when piped into head
    main()
