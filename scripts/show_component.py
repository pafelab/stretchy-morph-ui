#!/usr/bin/env python3
"""Print one showcase component: catalog recipe, CSS, HTML and JS, from assets/showcase.html.

    python scripts/show_component.py --list
    python scripts/show_component.py NAME [--recipe] [--css] [--html] [--js]
    python scripts/show_component.py --selftest

NAME is a banner name (tabs), a catalog number (2 or #2), or a unique substring
of a banner name or catalog title. With no part flag all four parts are printed.
Line numbers refer to assets/showcase.html (1-based).
"""
import argparse
import re
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
SHOW_REL = 'assets/showcase.html'
COMP_REL = 'references/components.md'
SHOW = SKILL / SHOW_REL
COMP = SKILL / COMP_REL

BANNER = re.compile(r'^/\* -{10} (.+?) -{10} \*/$')
OPEN = re.compile(r'^\s*<!-- component: (.+?) -->$')
CLOSE = re.compile(r'^\s*<!-- /component: (.+?) -->$')
ROW = re.compile(r'^\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*`([^`]+)`\s*\|')
DECL = re.compile(r'^(?:function|const|let)\s+([A-Za-z_$][\w$]*)')
SEG = 'segmented with stretchy indicator'
ENGINE = 'one spring to rule them all'
CORE = ['Spring', 'edgePair', 'makeSegmented', 'makeAccordion', 'onResync', 'flipReorder',
        'throwTo', 'volumeScale', 'alongVelocity', 'edgeBulge', 'rightEdgePath', 'topEdgePath',
        'replayClass', 'setBounce']


def norm(s):
    return ' '.join(s.lower().split())


def trim(lines, s, e):
    while e > s and not lines[e - 1].strip():
        e -= 1
    return e


def load():
    if not SHOW.is_file() or not COMP.is_file():
        print('missing file: %s or %s under %s' % (SHOW_REL, COMP_REL, SKILL))
        sys.exit(2)
    show = SHOW.read_text(encoding='utf-8').splitlines()
    comp = COMP.read_text(encoding='utf-8').splitlines()
    return show, comp


def catalog(comp):
    cat = {}
    for line in comp:
        m = ROW.match(line)
        if m:
            cat[int(m.group(1))] = (m.group(2).strip(), m.group(3).strip())
    return cat


def find_block(show, lo, hi, name):
    """0-based [s, e) of the banner section `name` between lo and hi, or None."""
    for i in range(lo, hi):
        m = BANNER.match(show[i])
        if m and norm(m.group(1)) == norm(name):
            e = hi
            for j in range(i + 1, hi):
                if BANNER.match(show[j]):
                    e = j
                    break
            return i, trim(show, i, e)
    return None


def recipe_block(comp, n):
    pat = re.compile(r'^(### |\*\*)%d\. ' % n)
    nxt = re.compile(r'^(### |\*\*)\d+\. ')
    for s, line in enumerate(comp):
        if pat.match(line):
            e = len(comp)
            for j in range(s + 1, len(comp)):
                if nxt.match(comp[j]):
                    e = j
                    break
            while e > s and not comp[e - 1].strip():
                e -= 1
            return comp[s:e]
    return None


def markers(show, name):
    """List of 0-based (open, close) index pairs for `<!-- component: name -->`."""
    pairs, pending = [], {}
    for i, line in enumerate(show):
        m = OPEN.match(line)
        if m:
            pending[norm(m.group(1))] = i
            continue
        m = CLOSE.match(line)
        if m:
            key = norm(m.group(1))
            if key not in pending:
                raise ValueError('close without open: %s line %d' % (key, i + 1))
            pairs.append((key, pending.pop(key), i))
    return [(o, c) for key, o, c in pairs if key == norm(name)]


def js_sections(show, lo, hi):
    bl = [(i, BANNER.match(show[i]).group(1)) for i in range(lo, hi) if BANNER.match(show[i])]
    out = []
    for k, (i, name) in enumerate(bl):
        e = bl[k + 1][0] if k + 1 < len(bl) else hi
        out.append((name, i, e))
    return out


TOKEN_MAP = {'violet': 'accent', 'pink': 'accent-2', 'teal': 'ok', 'stage-v': 'stage'}
TOKEN_SHARED = {'bg', 'surface', 'ink', 'muted', 'line'}
LIGHT_ROOT = re.compile(r':root\s*\{([^}]*)\}')
DARK_ROOT = re.compile(r':root\[data-theme="dark"\]\s*\{([^}]*)\}')
VAR_DEF = re.compile(r'(--[\w-]+)\s*:\s*([^;}]+)')
VAR_USE = re.compile(r'var\(\s*--([\w-]+)')
STRIP = re.compile(r'`(?:\\.|[^`\\])*`|\'(?:\\.|[^\'\\\n])*\'|"(?:\\.|[^"\\\n])*"|/\*.*?\*/|//[^\n]*', re.S)
DECL_KW = re.compile(r'\b(?:const|let|var)\b')
FUNC_NAME = re.compile(r'\bfunction\s+([A-Za-z_$][\w$]*)')
ARROW_ONE = re.compile(r'([A-Za-z_$][\w$]*)\s*=>')
ARROW_PARAMS = re.compile(r'\(([^()]*)\)\s*=>')
FUNC_PARAMS = re.compile(r'\bfunction\b\s*[\w$]*\s*\(([^()]*)\)')
LEAD_ID = re.compile(r'\s*\.{0,3}([A-Za-z_$][\w$]*)')


def token_line(light, dark, text):
    """One line mapping the colour tokens used in `text` to starter names, or None."""
    seen = []
    for n in VAR_USE.findall(text):
        if n not in seen:
            seen.append(n)
    out = []
    for n in seen:
        if n in TOKEN_SHARED:
            continue
        if n in TOKEN_MAP:
            out.append('--%s = starter --%s' % (n, TOKEN_MAP[n]))
        elif '--' + n in light:
            vals = ['light %s' % light['--' + n]]
            if '--' + n in dark:
                vals.append('dark %s' % dark['--' + n])
            out.append('--%s is showcase-only (%s)' % (n, ', '.join(vals)))
    return 'tokens: ' + ', '.join(out) if out else None


def strip_code(text):
    """Remove string literals and comments (best effort)."""
    return STRIP.sub(' ', text)


def local_names(code):
    """Names this code declares (const/let/var/function) or takes as parameters (best effort)."""
    names = set(m.group(1) for m in FUNC_NAME.finditer(code))
    for m in DECL_KW.finditer(code):
        out, depth, j = '', 0, m.end()
        while j < len(code):
            ch = code[j]
            if ch in '([{':
                depth += 1
            elif ch in ')]}':
                if depth == 0:
                    break
                depth -= 1
            elif depth == 0 and (ch == ';' or (ch == '\n' and not out.rstrip().endswith(','))):
                break
            out += ch
            j += 1
        pieces, piece, depth = [], '', 0
        for ch in out:
            if ch in '([{':
                depth += 1
            elif ch in ')]}':
                depth -= 1
            if ch == ',' and depth == 0:
                pieces.append(piece)
                piece = ''
            else:
                piece += ch
        pieces.append(piece)
        for p in pieces:
            pm = LEAD_ID.match(p)
            if pm:
                names.add(pm.group(1))
    names.update(ARROW_ONE.findall(code))
    for rx in (ARROW_PARAMS, FUNC_PARAMS):
        for m in rx.finditer(code):
            for p in m.group(1).split(','):
                pm = LEAD_ID.match(p)
                if pm:
                    names.add(pm.group(1))
    return names


def resolve(arg, cat, show_names):
    key = norm(arg)
    if key.startswith('#'):
        key = key[1:].strip()
    if not key:
        return None
    if key.isdigit():
        n = int(key)
        return cat[n][1] if n in cat else None
    for name in show_names:
        if norm(name) == key:
            return name
    cands = set()
    for title, banner in cat.values():
        if key in norm(banner) or key in norm(title):
            cands.add(banner)
    for name in show_names:
        if key in norm(name):
            cands.add(name)
    return cands.pop() if len(cands) == 1 else None


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser(description='Print one showcase component.')
    ap.add_argument('name', nargs='?')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    for flag in ('recipe', 'css', 'html', 'js'):
        ap.add_argument('--' + flag, action='store_true')
    args = ap.parse_args()

    show, comp = load()
    cat = catalog(comp)
    style_open = show.index('<style>')
    style_close = next(i for i in range(style_open, len(show)) if show[i].strip() == '</style>')
    script_open = show.index('<script>')
    script_close = next(i for i in range(script_open, len(show)) if show[i].strip() == '</script>')
    css_names = [BANNER.match(show[i]).group(1) for i in range(style_open, style_close) if BANNER.match(show[i])]
    js = js_sections(show, script_open + 1, script_close)
    show_names = list(dict.fromkeys(css_names + [n for n, _, _ in js]))
    cat_names = [cat[n][1] for n in sorted(cat)]
    lm = LIGHT_ROOT.search('\n'.join(show))
    dm = DARK_ROOT.search('\n'.join(show))
    light = {k: v.strip() for k, v in VAR_DEF.findall(lm.group(1))} if lm else {}
    dark = {k: v.strip() for k, v in VAR_DEF.findall(dm.group(1))} if dm else {}

    if args.list:
        for n in sorted(cat):
            title, banner = cat[n]
            print('%d  %s  -  %s' % (n, banner, title))
        return 0

    if args.selftest:
        bad = []
        for n in sorted(cat):
            title, banner = cat[n]
            if not recipe_block(comp, n):
                bad.append('%s: recipe' % banner)
            if not find_block(show, style_open, style_close, banner):
                bad.append('%s: css' % banner)
            if not markers(show, banner):
                bad.append('%s: html' % banner)
            blk = find_block(show, script_open + 1, script_close, banner)
            if not blk or blk[1] <= blk[0]:
                bad.append('%s: js' % banner)
        for line in bad:
            print('missing ' + line)
        if bad:
            return 1
        print('ok: %d components' % len(cat))
        return 0

    if args.name is None:
        ap.error('NAME, --list or --selftest is required')
    name = resolve(args.name, cat, show_names)
    if name is None:
        print('unknown component "%s". Names: %s' % (args.name, ', '.join(cat_names)))
        return 2

    parts = [p for p in ('recipe', 'css', 'html', 'js') if getattr(args, p)] or ['recipe', 'css', 'html', 'js']
    num = next((n for n in cat if cat[n][1] == name), None)

    for part in parts:
        if part == 'recipe':
            if num is None:
                continue
            print('=== recipe: #%d %s (%s) ===' % (num, cat[num][0], COMP_REL))
            for line in recipe_block(comp, num) or ['(entry not found)']:
                print(line)
        elif part == 'css':
            blk = find_block(show, style_open, style_close, name)
            print('=== css (%s lines %d-%d) ===' % (SHOW_REL, blk[0] + 1, blk[1]) if blk else '=== css (not found) ===')
            if blk:
                print('\n'.join(show[blk[0]:blk[1]]))
            used = '\n'.join(show[blk[0]:blk[1]]) if blk else ''
            sec = find_block(show, script_open + 1, script_close, name)
            if sec and re.search(r'makeSegmented\s*\(', '\n'.join(show[sec[0]:sec[1]])):
                shared = find_block(show, style_open, style_close, SEG)
                if shared:
                    print('=== css shared: %s (%s lines %d-%d) ===' % (SEG, SHOW_REL, shared[0] + 1, shared[1]))
                    print('\n'.join(show[shared[0]:shared[1]]))
                    used += '\n' + '\n'.join(show[shared[0]:shared[1]])
            for o, c in markers(show, name):
                used += '\n' + '\n'.join(show[o + 1:c])
            if sec:
                used += '\n' + '\n'.join(show[sec[0]:sec[1]])
            line = token_line(light, dark, used)
            if line:
                print(line)
        elif part == 'html':
            pairs = markers(show, name)
            if not pairs:
                print('=== html (not found) ===')
            for o, c in pairs:
                body = show[o + 1:c]
                while body and not body[-1].strip():
                    body.pop()
                print('=== html (%s lines %d-%d) ===' % (SHOW_REL, o + 2, o + 1 + len(body)))
                print('\n'.join(body))
        elif part == 'js':
            sec = find_block(show, script_open + 1, script_close, name)
            if not sec:
                print('=== js (not found) ===')
                continue
            s, e = sec
            print('=== js (%s lines %d-%d) ===' % (SHOW_REL, s + 1, e))
            print('\n'.join(show[s:e]))
            text = '\n'.join(show[s:e])
            used = []
            for fn in CORE:
                pat = r'\bnew Spring\b|\bSpring\s*\(' if fn == 'Spring' else r'\b%s\s*\(' % fn
                if re.search(pat, text):
                    used.append(fn)
            print('helpers from the core: %s' % (', '.join(used) if used else 'none'))
            declared = {}
            for sname, si, se in js:
                if sname == ENGINE or sname == name or si < script_open + 1:
                    continue
                for line in show[si:se]:
                    m = DECL.match(line)
                    if m and m.group(1) not in declared:
                        declared[m.group(1)] = sname
            code = strip_code(text)
            local = local_names(code)
            also = [(ident, sname) for ident, sname in declared.items()
                    if ident not in local and re.search(r'(?<![\w$])%s(?![\w$])' % re.escape(ident), code)]
            if also:
                print('also uses from other showcase sections: %s' % ', '.join('%s (%s)' % a for a in also))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        print('error: %s' % exc)
        sys.exit(2)
