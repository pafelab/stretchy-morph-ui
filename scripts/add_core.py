"""Turn assets/stretchy-core.js into an ES module, or keep a page's inline copy in sync.

Exactly one mode per run:
  --module DEST.js         write the core as an ES module (top-level declarations get `export`)
  --inline PAGE.html       replace the lines between `/* CORE START` and `/* CORE END */` with the core
  --check [PAGE.html]      exit 1 when that block differs from the core (default assets/starter.html)

Standard library only, Python 3.8+.
"""
import argparse
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
CORE = SKILL / 'assets' / 'stretchy-core.js'
DEFAULT_PAGE = SKILL / 'assets' / 'starter.html'
START = '/* CORE START'
END = '/* CORE END */'
DECL = ('const ', 'let ', 'function ', 'class ')


def fail(msg, code=2):
    print(msg)
    sys.exit(code)


def read(path):
    with open(str(path), encoding='utf-8', newline='') as f:
        return f.read()


def write(path, text):
    with open(str(path), 'w', encoding='utf-8', newline='') as f:
        f.write(text)


def core_text(eol):
    """The core with exactly one trailing line break, in the given line-ending style."""
    text = read(CORE).replace('\r\n', '\n').rstrip('\n') + '\n'
    return text.replace('\n', eol)


def to_module(text):
    out, n = [], 0
    for line in text.split('\n'):
        if line.startswith(DECL):
            line = 'export ' + line
            n += 1
        out.append(line)
    return '\n'.join(out), n


def find_block(lines):
    """Return (start, end) line indexes of the marker lines, or exit 2 with one line."""
    starts = [i for i, ln in enumerate(lines) if ln.startswith(START)]
    if not starts:
        fail('no `/* CORE START` marker line in the page')
    if len(starts) > 1:
        fail('CORE START appears %d times in the page (expected once)' % len(starts))
    s = starts[0]
    ends = [i for i in range(s + 1, len(lines)) if lines[i].rstrip() == END]
    if not ends:
        fail('no `/* CORE END */` marker line after CORE START')
    return s, ends[0]


def page_parts(page_path):
    """Split a page into (text, lines, start, end, eol, current block text)."""
    text = read(page_path)
    eol = '\r\n' if '\r\n' in text else '\n'
    lines = text.split('\n')
    s, e = find_block(lines)
    block = '\n'.join(lines[s + 1:e]) + ('\n' if e > s + 1 else '')
    return lines, s, e, eol, block


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--module', metavar='DEST.js', help='write the core as an ES module')
    g.add_argument('--inline', metavar='PAGE.html', help='replace the marked block in PAGE with the core')
    g.add_argument('--check', nargs='?', const='', metavar='PAGE.html',
                   help='compare the marked block with the core (default assets/starter.html)')
    p.add_argument('--force', action='store_true', help='with --module: overwrite an existing DEST')
    args = p.parse_args()

    if not CORE.is_file():
        fail('core not found: %s' % CORE)

    try:
        if args.module:
            dest = Path(args.module)
            if dest.exists() and not args.force:
                fail('refused: %s exists (use --force to overwrite)' % args.module)
            body, n = to_module(read(CORE).replace('\r\n', '\n'))
            dest.parent.mkdir(parents=True, exist_ok=True)
            write(dest, body)
            print('wrote ES module: %s (%d exports, %d bytes)' % (args.module, n, len(body.encode('utf-8'))))
            return 0

        if args.inline is not None:
            page = Path(args.inline)
            if not page.is_file():
                fail('page not found: %s' % args.inline)
            lines, s, e, eol, block = page_parts(page)
            want = core_text(eol)
            if block == want:
                print('already up to date: %s' % args.inline)
                return 0
            new = '\n'.join(lines[:s + 1]) + '\n' + want + '\n'.join(lines[e:])
            write(page, new)
            print('inlined core into %s (%d bytes of core)' % (args.inline, len(want.encode('utf-8'))))
            return 0

        name = args.check or str(DEFAULT_PAGE)
        page = Path(name)
        if not page.is_file():
            fail('page not found: %s' % name)
        lines, s, e, eol, block = page_parts(page)
        if block == core_text(eol):
            print('in sync: %s' % name)
            return 0
        print('OUT OF SYNC: %s (run: python scripts/add_core.py --inline %s)' % (name, name))
        return 1
    except OSError as err:
        fail('file error: %s' % err)


if __name__ == '__main__':
    sys.exit(main())
