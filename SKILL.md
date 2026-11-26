---
name: stretchy-morph-ui
description: Make web UI morph like rubber, with springs that squash, stretch, overshoot and settle instead of easing curves. Use whenever the user wants animated, bouncy, elastic, gooey or alive-feeling UI, micro-interactions or morph transitions, or asks which parts of their interface could feel more fluid, even if they never say spring. Thai triggers include UI ยืดได้, ยืดหยุ่น, เด้ง, morph ตอน transition, ทำให้ UI ดูมีชีวิต, ตรวจโค้ดว่าทำให้ยืดได้ตรงไหน.
license: MIT
---

# Stretchy morph UI

This skill produces interfaces where every state change *morphs*: a tab indicator stretches like a worm on its way to the next tab, a button squeezes into a loading circle and swells back, a product picture lifts off its card, shrinks into a chip and drops into the cart.

The look comes from one idea: **stretch is caused by something.** An element deforms because its parts disagree (one edge arrives before the other), because it is moving fast (it lengthens along its path), because it is being squeezed (it bulges the other way to keep its volume), or because it was just hit (it wobbles). Random wobble on a loop looks cheap; stretch with a cause looks like material.

## Spend tokens on the design, not on files

- **Copy, never re-type.** A standalone page is a copy of `assets/starter.html` (`cp` / `Copy-Item`), which carries the whole core inline between the lines `/* CORE START` and `/* CORE END */`. Find them with `grep -n "CORE START\|CORE END" page.html`, then Read (with offset and limit) and Edit only the lines outside that block. Never Read the core to paste it, and never emit it yourself.
- **One component, one command.** `python scripts/show_component.py NAME` prints a catalog component's recipe, CSS, markup and JS. Never Read `assets/showcase.html` whole (166 KB), and never port its engine: use the core.
- **Read references by section**: `grep -n "^##" references/<file>.md`, then Read only that range.

## Step 0: audit existing code, then confirm

Only when the request is about the user's existing interface in general ("make my app feel alive", "what could stretch here", a repo, files, or live URL in scope with no specific parts named). Read `references/audit.md` and follow it: find the code or URL, scan it with `python scripts/audit_ui.py <paths-or-urls>` (add `--dom` for rendered-DOM inspection of local HTML, or `--stdin --ext .tsx` for pasted snippets), read every hit in context, prioritise, then send the numbered proposals in the user's language and ask which to build. **End the turn there; make no edits before the reply.** If there is no code or URL anywhere, say what you looked for and offer two paths: share the code/URL, or build something new from scratch.

Skip the audit when the user asks for something new ("build a stretchy toggle") or already named the parts to change ("make my tabs stretchy"): go straight to the Workflow. For a named part in a codebase, read that part's file first, then only the matching recipe. If you noticed other good candidates along the way, mention them in one line at the end.

## Files

Paths are relative to this skill's folder (the folder containing this `SKILL.md`), not to the user's project. Open only what the task needs.

| Path | Use |
|---|---|
| `assets/starter.html` | Page skeleton: light/dark tokens, Thai-capable variable font, reduced-motion CSS, the core inline, one tabs example. Copy it to start a standalone page |
| `assets/stretchy-core.js` | The spring engine and helpers. Copy it, or `python scripts/add_core.py --module <dest.js>` for an ES module. Read it only to change the engine |
| `references/core-api.md` | Helper signatures, spring presets, runtime cost rules. Read before writing spring code |
| `scripts/show_component.py` | `NAME` prints one of the 31 showcase components with its recipe from `references/components.md` (`--list` for the names; `--recipe`, `--css`, `--html`, `--js` for one part). Use when the request names or resembles a catalog component |
| `references/techniques.md` | The 11 stretch techniques with code and tuning numbers. Read the sections for techniques you have not built before |
| `references/new-components.md` | The method for any component, plus 13 worked designs. Read when the request is outside the catalog |
| `references/frameworks.md` | React, Vue, Svelte, component libraries, server-rendered sites. Read when the target is a codebase rather than a new page |
| `references/audit.md`, `scripts/audit_ui.py` | Step 0 only |
| `references/pitfalls.md` | Symptom, cause, fix table and the polish lessons from the build. Read when a page misbehaves or looks cheap, and before porting a catalog component |
| `scripts/check_page.py` | Headless check of a file or URL (JS errors, sideways overflow, invisible click blockers, contact sheets, jump strips). Run after every build, before you hand anything over |

If a visual design skill is available (for example `frontend-design` or `ui-ux-pro-max`), read it too: it decides how the page looks, this one decides how it moves. Motion polish cannot rescue a generic-looking page.

## Workflow (after the user confirms)

1. **Write the morph sentence for each component.** "When *trigger*, *shape A* becomes *shape B*, and it stretches because *cause*." Example: "When a tab is clicked, the indicator moves to it, and it stretches because its leading edge is stiffer than its trailing edge." If you cannot fill in the cause, pick one from the table below. This sentence is the design; everything else is implementation.
2. **Pick the technique(s)** from the table. Most components use one primary stretch plus one small feedback wobble.
3. **Define resting states as numbers**: widths, heights, radii, positions, progress 0 to 1. Springs animate numbers and you write them to `style` in `onUpdate`. CSS transitions handle only colour and opacity (and short content crossfades).
4. **Plan the content.** Text and icons must not reflow or squash while the container morphs. Give each content state its own layer at its final size, anchored (usually centred), and crossfade: exit fast (≈150 ms), enter after a ≈100–150 ms delay with a slight scale or blur. The container's `overflow:hidden` reveals content as it grows.
5. **Build.** Standalone page: in your copy of the starter, replace the tabs example (the CSS block headed `Example: worm tab bar`, its `<article>`, and the script lines after `/* CORE END */`) and keep the shell and the core. Showcase CSS uses its own colour tokens; `show_component.py` prints how they map to the starter's. Codebase or existing site: follow `references/frameworks.md`. Write styles directly in spring callbacks; never trigger a framework re-render per frame.
6. **Accessibility and interruption pass** (checklist below).
7. **Test and look.** `python scripts/check_page.py <page.html or http://localhost:PORT/route> --frames "CLICK_SELECTOR@CLIP_SELECTOR"` (one `--frames` per important interaction; clip to an area a few hundred pixels wide so the frames are readable). It prints its output folder. Open the contact sheets and every `jump_N.png` strip (each tab or radio group jumping from its first item to its last in slow motion, one frame per row; `--jumps SELECTOR` adds groups) and check the two indicator rules below in every row. A clean exit code says nothing about how it looks: the first add-to-cart animation "worked" but looked cheap until its frames were inspected. When a frame looks cheap, the fixes are in `references/pitfalls.md`.

## Where the stretch comes from

Code, numbers and working examples for each technique: `references/techniques.md`.

| Situation | Technique |
|---|---|
| Something moves between slots | **Edge pair**: two springs for leading and trailing edges, leading one stiff, swapped by direction |
| A container changes size or shape | **Split axes**: separate springs for width, height, radius with different stiffness, so one axis leads |
| Something gets narrower or wider fast | **Volume preservation**: scale the other axis by velocity, `scaleY = clamp(1 − v/k)` |
| Something travels fast | **Velocity stretch**: lengthen along the direction of motion, thin across it |
| A big surface moves | **Bulging edge**: draw the surface as an SVG path whose edge control point is offset by −velocity |
| A part hangs off a moving part | **Lagging follower**: a softer spring chases the main one; use the gap for tilt or offset |
| Feedback for a tap or arrival | **Kick**: add velocity to a spring resting at 0, it wobbles and settles |
| Blobs join or split | **Goo filter**: blur plus alpha threshold, sharp source composited on top |
| An element becomes a different element | **Container transform**: start at the trigger's rect, spring to the target rect, crossfade content |
| The change needs a pause in between | **Sequenced morph through an intermediate shape** that carries meaning (spinner, check) |
| Dragging past a limit, or a list reorders | **Rubber band** (divide overscroll by ≈3) and **FLIP with springs** that keep velocity |

## The engine in one paragraph

`Spring` is a damped oscillator. `to(target)` retargets **without resetting velocity**, which is what makes rapid clicks feel continuous instead of restarting. `set(x)` jumps without animation, `drag(x, v)` follows a pointer while recording velocity, `kick(v)` injects an impulse. Damping is multiplied by a global `bounce` factor at every tick, so one page-level control (soft 1.8, bouncy 1, stretchy 0.5) re-tunes every component live. Under `prefers-reduced-motion: reduce`, `to()` snaps to the target and fires `onRest` immediately, so logic that waits for an animation still runs.

Damping ratio ζ = c / (2√k). UI state changes feel right around ζ 0.6–0.8; playful feedback at 0.3–0.5; above 1 nothing overshoots. Preset `k` and `c` for each role, and every helper's signature: `references/core-api.md`.

## Rules of thumb

- **Cap every deformation.** Controls: volume preservation within ±7–15 %. Small fast things (a thrown chip, a slider thumb): up to 35–70 % stretch. Always clamp sizes to a positive minimum, since an underdamped spring can undershoot below zero.
- **Swap stiffness by direction.** In an edge pair, whichever edge faces the direction of travel gets the stiff spring. Without the swap, the indicator stretches correctly one way and compresses the other.
- **Opposite timing on the way back.** If width leads height when opening, let height lead width when closing. The shape then retraces a different path, which reads as elastic instead of a rewind.
- **Springs for state changes, time-based curves for paths whose shape matters.** A thrown object needs a predictable arc (quadratic Bézier, ease-in-out progress, around 800 ms). Independent x/y springs give wandering paths. Derive stretch from the frame-to-frame velocity either way.
- **Keep content upright.** To stretch something along an arbitrary direction without rotating its picture or text, use `rotate(a) scale(1+s, 1−s·0.45) rotate(−a)`.
- **One bold motion per component.** The rest of the component stays quiet: a colour change, a short fade.
- **Calm when idle.** Nothing wobbles on its own. At most one orchestrated moment on page load (the showcase opens the island once after 900 ms).

## Moving indicators: two rules that break when porting

Any component where one shape travels to the chosen item (worm tabs, choice chips, segmented controls, radio dots, nav highlights, rating capsules) depends on two things besides its springs. Ports lose them first: the picked item vanishes for about 0.2 s, or the indicator shows only in the gaps between items.

1. **The selected look arrives with the indicator, not with the click.** Update `aria-selected`/`aria-checked`, focus and app state on click. Switch the *visual* selected style (light label, transparent or coloured fill, hidden border) only on the first frame the indicator covers the item; the core's `makeSegmented` adds `.on` from the indicator's draw callback once it covers the button, and the showcase's choice chips add `.cc-on` the same way. Until then the item keeps its unselected look. If the style switches on click, a light label sits on a light surface while the indicator is still on its way, and the item disappears. Styling `[aria-checked=true]` or a framework's `selected` prop directly does exactly that, so bind the visual style to a separate class that the animation sets.
2. **The indicator paints above item surfaces and below item content.** Container: `position:relative; isolation:isolate`. Item surface **and border**: a `::before` with `z-index:-2` (the item itself has no `background`, no visible `border` and no `z-index`; keep a transparent border on it if the box size depends on it). Indicator: `z-index:-1`, `pointer-events:none`. Only labels and icons paint on top. A border left on the item paints over the indicator as a ring on every item it crosses. If items keep their own background (component libraries usually do), the indicator slides *behind* every item it crosses and shows only in the gaps, so the worm reads as broken pieces and the slow trailing edge looks like it is stuck behind the neighbour. When the library cannot be restyled, override its surface to transparent and draw the surfaces yourself.

When you port any catalog component into an existing codebase or component library, copy its layer order and the timing of its state classes, not only its springs. Diff the CSS of the stateful classes against the showcase.

## Accessibility and robustness checklist

- Respect reduced motion (the core does it; make sure CSS keyframes and transitions are also cut in a `prefers-reduced-motion` media query).
- Use real `button`, `input`, `role="switch"`, `role="tab"`, `role="slider"` etc. with the right `aria-*` state, updated in the same call that starts the animation.
- Content that is hidden by a morph gets `inert` (and must not intercept clicks: give invisible layers `pointer-events:none`, then switch it back on with the visible state).
- Move focus deliberately when the focused control disappears into a morph: to the replacement control, back to the trigger after a dialog closes, and only after the element is visible again (a `visibility:hidden` element cannot take focus).
- Keyboard paths: arrows for indicators, sliders, radios and listboxes; Esc closes overlays; Tab is trapped in modal dialogs.
- Announce results that are only visible as motion (`aria-live` status text: "ส่งแล้ว", "เพิ่มลงตะกร้าแล้ว").
- Measure after fonts load and on resize: register a resync function per component (`onResync` in the core) that `set()`s springs to freshly measured positions.

## Traps on every build

- Block stages need `place-items:normal`: `place-items:center` on a `display:block` container shrink-wraps and centres block children in Chromium.
- Grid columns: `minmax(0,1fr)`, not `1fr`, or a child's min-content (a carousel track) makes the whole page scroll sideways on phones.
- Pixel springs whose `onRest` triggers logic take `eps: 0.5` (the rest threshold). At the default 0.05 px a dialog lingers about 1 s after it visibly closed.
- Unique helper names in one script: a second `function setVal` silently replaces the first. Check with `grep -oE "function [A-Za-z_]+" page.html | sort | uniq -d`.

More symptoms with their fixes, and the polish lessons from the build (move the real thing, intermediate shapes must carry meaning, arrival needs a receiver): `references/pitfalls.md`.

## Delivering

- Standalone demo: one self-contained HTML file (the copied starter, CSS and JS inline). Load fonts from Google Fonts with a real fallback stack. Respect the host's dark/light handling. Claude (claude.ai or Claude Code with artifact publishing): publish the file as an artifact. Antigravity: save it in the workspace and open it in the built-in browser to watch the interactions. Anywhere else: save the file and tell the user its path.
- Codebase: keep the core as one module, create springs once, write styles to element refs inside `onUpdate`, keep component state in the framework, stop the springs on unmount. Details and a React port: `references/frameworks.md`.
- Write UI copy in the user's language. If they write in Thai, the demo content is Thai, and a variable Thai-capable font such as Noto Sans Thai (with its width axis for condensed headlines) is a good default.
