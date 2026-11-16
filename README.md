# stretchy-morph-ui

A skill for AI coding agents (Claude and Google Antigravity) that gives web UIs **rubbery, elastic morphing**: elements squish, stretch, overshoot their target, and settle into place using physical springs instead of easing curves.

For example: a tab underline that stretches like an inchworm to the next tab, a button that collapses into a loading ring and inflates back, or a product image that lifts off its card, compresses into a circle, and drops into the cart.

> **The core principle of this skill:** Stretch must have a physical cause.
> The leading edge arrives before the trailing edge; fast movement stretches along the direction of travel; compression along one axis bulges the other to preserve volume; or an impact induces oscillation.
> Aimless wobbling looks cheap, but purposeful deformation feels like real physical matter.

## What's Included

- **Zero-dependency Spring Engine** (`assets/stretchy-core.js`) with helper utilities including edge pairs, volume preservation, bulging SVG edges, FLIP reordering, thrown objects, and `makeAccordion` to make existing `<details>` elements instantly elastic.
- **24 Working Showcase Components**: tabs, stepper, sidebar, carousel, send button, toggles, radio/checkbox, chips, search, dropdown, slider, quantity, rating, add to cart, goo menu, modal, toast, tooltip, bottom sheet, FAB, accordion, dynamic island, date picker (single or range selection), and choice chips (single-select chips).
- **11+ Elastic Deformation Techniques** with code recipes and tuned spring presets.
- **Guide for Designing New Components** not in the catalog, featuring 13 worked designs (pull-to-refresh, swipe-to-delete, OTP input, etc.). The React port of the `WormTabs` component moved to a frameworks guide, which also covers Vue, Svelte, component libraries and server rendering.
- **Component extractor** (`scripts/show_component.py`): prints one showcase component by name (`--recipe`, `--css`, `--html`, `--js`), so the showcase page never has to be read whole. `--list` shows all 24.
- **Core tool** (`scripts/add_core.py`): writes the spring engine as an ES module for React, Vue or Svelte (`--module`), and keeps a standalone page's inline copy of the core in sync (`--inline`, `--check`).
- **API cheat sheet** (`references/core-api.md`): signatures of every helper, the spring preset table and runtime cost rules.
- **Pre-flight Code Audit Workflow** (Step 0, when asked to generally enhance existing UI without specific targets): scan existing code using `scripts/audit_ui.py` to identify candidates for elasticity (tabs, toggles, modals, dropdowns, accordions, etc.), summarize findings with `file:line`, and ask the user to confirm or customize **before modifying any files**.
- **Page Inspection Script** powered by headless Chromium: detects JavaScript errors, horizontal overflow, invisible click-blocking layers, and captures animation frames arranged into a contact sheet.

## Structure

```
stretchy-morph-ui/
├── SKILL.md                    Main instructions read by the agent (workflow, rules, checklist)
├── references/
│   ├── audit.md                How to identify, scan, decide, and rank candidate elements + confirmation templates (TH/EN)
│   ├── techniques.md           Deformation techniques, code, and tuning parameters
│   ├── components.md           Component catalog: recipes, spring values, gotchas
│   ├── new-components.md       Designing new components + 13 worked designs
│   ├── core-api.md             Helper signatures, spring presets, runtime cost rules
│   ├── frameworks.md           Using the core in React, Vue, Svelte, component libraries, server rendering
│   └── pitfalls.md             Pitfalls from real builds + lessons on making motion look good
├── assets/
│   ├── stretchy-core.js        Spring engine + helpers
│   ├── starter.html            Starter template (light/dark mode, Thai typography, reduced motion)
│   └── showcase.html           All 24 showcase components
└── scripts/
    ├── audit_ui.py             Scans user code: tech stack, existing animations, elasticity candidates
    ├── add_core.py             Writes the core as an ES module, or syncs a page's inline copy
    ├── show_component.py       Prints one showcase component (recipe, CSS, HTML, JS)
    └── check_page.py           Smoke testing + animation frame capture
```

## Installation

This skill follows the standard `SKILL.md` format (YAML frontmatter with `name` + `description`), allowing the exact same folder to be used in both Claude and Antigravity without file conversion. Simply clone it into the skills directory for your tool of choice.

| Tool | Global (All Projects) | Workspace (Project Only) |
|---|---|---|
| Claude Code | `~/.claude/skills/stretchy-morph-ui/` | `.claude/skills/stretchy-morph-ui/` |
| Antigravity (IDE & `agy` CLI) | `~/.gemini/config/skills/stretchy-morph-ui/` | `.agents/skills/stretchy-morph-ui/` |

### Claude Code

```bash
# Global (all projects)
git clone <repo-url> ~/.claude/skills/stretchy-morph-ui

# Project only
git clone <repo-url> .claude/skills/stretchy-morph-ui
```

### Antigravity

```bash
# Global (all projects)
git clone <repo-url> ~/.gemini/config/skills/stretchy-morph-ui

# Project only (commit .agents/ to git to share with your team)
git clone <repo-url> .agents/skills/stretchy-morph-ui
```

Antigravity also accepts `.agent/`, `_agents/`, and `_agent/` in place of `.agents/`, searching upwards from the active folder to the repository root.

To store the repository elsewhere, register the skill's parent directory in `skills.json` (placed in `~/.gemini/config/` or the project's `.agents/`). Antigravity scans one level down inside each configured `path`:

```json
{
  "entries": [
    { "path": "~/src/my-skills", "include_only": ["stretchy-morph-ui"] }
  ]
}
```

### Shared Setup for Both Tools (Windows)

Clone once, then create a directory junction pointing from the other location. Edits immediately reflect in both tools (junctions on Windows require no admin privileges):

```powershell
git clone <repo-url> "$HOME\.claude\skills\stretchy-morph-ui"
New-Item -ItemType Junction -Path "$HOME\.gemini\config\skills\stretchy-morph-ui" `
         -Target "$HOME\.claude\skills\stretchy-morph-ui"
```

On macOS / Linux, use:
```bash
ln -s ~/.claude/skills/stretchy-morph-ui ~/.gemini/config/skills/stretchy-morph-ui
```

### claude.ai

Zip this folder (ensuring `stretchy-morph-ui/` is at the top level of the archive) and upload it under Settings → Capabilities → Skills:

```bash
zip -r stretchy-morph-ui.skill stretchy-morph-ui -x "*.git*"
```

## Usage

You do not need to invoke the skill manually. The coding agent (Claude or Antigravity) automatically activates it whenever your prompt involves dynamic or animated UI, for instance:

- "Build tabs where the active indicator stretches when switching."
- "Create an 'Add to Cart' button where the product image flies into the basket."
- "Make this page feel more alive and bouncy."
- "Make this toggle feel more springy / gooey / elastic."

### Using the Spring Engine Standalone

`stretchy-core.js` can be used completely independently of the skill. Simply include it via a `<script>` tag (exposing globals), or write an ES module copy with `python scripts/add_core.py --module src/lib/stretchy-core.js`; the module is safe to import during server rendering. Example:

```js
const box = document.querySelector('.box');

const w = new Spring(120, {
  k: 280, c: 20,                       // stiffness, damping
  onUpdate: x => box.style.width = x + 'px',
});

w.to(320);      // Animate to target while preserving current momentum (handles rapid clicks seamlessly)
w.kick(8);      // Impulse nudge that oscillates and settles
setBounce(0.5); // Global bounciness multiplier: 1.8 soft/stiff, 1 balanced bounce, 0.5 highly elastic
```

Easily wrap existing accordions to make them smoothly stretch. Supports native `<details>` elements (which remain functional without JavaScript and allow browser find-in-page to automatically reveal matching items) as well as button + panel markup:

```js
const faq = makeAccordion(document.querySelector('.faq'), { gap: 6 }); // details sharing the same name = mutually exclusive
faq.single = false;  // Allow multiple panels open simultaneously
faq.open(0);         // Programmatically open first panel
faq.destroy();         // remove listeners and stop springs (call on unmount in a single-page app)
```

In a single-page app, also call `spring.stop()` on each `Spring` (it halts in place, keeping its value and target) and the function that `onResync(f)` returned when the component unmounts.

When `prefers-reduced-motion: reduce` is active, `to()` instantly snaps to the target value and invokes `onRest` immediately, ensuring code awaiting animation completion continues to work seamlessly.

### Scanning Code for Elastic UI Candidates

Zero external dependencies required (pure Python). Accepts individual files or entire directories, supporting HTML/CSS/JS and modern frameworks:

```bash
python scripts/audit_ui.py ./src
python scripts/audit_ui.py ./src --json --max-hits 10
```

The report lists the detected stack and existing motion, then candidate hits grouped by UI category, each mapped to a showcase component and a technique. Paths are relative to the scanned root and hits are grouped per file; tests, stories, minified and generated files and comment lines are skipped; CSS-only matches are reported separately; shared components are listed with their use counts. This output is a heuristic-based screening; always inspect surrounding code before presenting suggestions to the user.

### Page Inspection & Smoke Testing

Requires Playwright. Its Chromium download is optional, because the script falls back to installed Edge or Chrome when it is missing (`--channel` picks one). It accepts a local file or a URL, and writes to a temp folder unless `--out` is given:

```bash
pip install playwright
playwright install chromium

# Check for console errors, horizontal overflow, and click blockers at 1280px and 390px widths
python scripts/check_page.py assets/showcase.html --out out/

# Same checks against a running dev server
python scripts/check_page.py http://localhost:5173/

# Click a selector and capture 8 frames spaced 110ms apart, cropped to .stage
python scripts/check_page.py page.html --frames "#tabs button:nth-child(3)@.stage"

# Also capture jump strips for a custom selection group (tabs and radio groups are found automatically)
python scripts/check_page.py page.html --jumps ".brand-filter button"
```

Frames and jump strips are captured in slow motion (`--slowmo 4` by default, `1` turns it off). A screenshot takes 100–200 ms, so at full speed a spring has nearly settled by the second frame.

For every tab and radio group the script saves `jump_N.png`: it selects the first item, clicks the last one, and stacks one frame per row. Look at the clicked item in every row. It must stay readable until the indicator reaches it, and the indicator must pass over the items it crosses, not hide behind them.

Exits with code 1 if errors, overflow or click blockers are detected, making it suitable for CI pipelines. Frames and jump strips are for review and never change the exit code.

## Token cost

- SKILL.md is kept small because it is loaded on every activation; details live in `references/` and are read by section.
- The agent copies `assets/starter.html` and never re-types the core.
- `scripts/show_component.py` prints one component, so the 162 KB showcase (`assets/showcase.html`) is never read whole.

## Common Spring Tuning Values

| Role | k | c |
|---|---|---|
| Leading edge of edge pair | 420–520 | 30–34 |
| Trailing edge of edge pair | 140–170 | 17–19 |
| Container width | 240–320 | 18–24 |
| Container height | 150–170 | 15–17 |
| Kick / Impulse feedback | 380–420 | 12–16 |

Damping ratio $\zeta = c / (2\sqrt{k})$: general state transitions typically range between 0.6–0.8, playful feedback between 0.3–0.5; values exceeding 1.0 will not overshoot.

For more details, see [`SKILL.md`](SKILL.md) and [`references/techniques.md`](references/techniques.md).
