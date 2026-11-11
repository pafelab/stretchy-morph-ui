---
name: stretchy-morph-ui
description: Turn web UI into stretchy morph UI, where transitions squash, stretch, overshoot and settle on springs instead of easing curves. When invoked, first audit the user's existing code for components that could become stretchy (tabs, toggles, buttons, modals, dropdowns, accordions, carousels, toasts, sidebars, date pickers, add to cart and more), then list what can change and ask the user to confirm or add their own requests before editing anything. Includes a spring engine, 23 working reference components, a scanner, a browser checker, and a method for inventing new stretchy components. Use whenever the user wants animated or alive-feeling UI, micro-interactions, spring, elastic, bouncy, gooey, liquid or morph transitions, or wants an existing interface to feel more fluid, tactile or playful, even if they never say spring. Thai triggers include UI ยืดได้, ยืดหยุ่น, เด้ง, morph ตอน transition, แอนิเมชันปุ่ม, ทำให้ UI ดูมีชีวิต, ตรวจโค้ดว่าทำให้ยืดได้ตรงไหน.
---

# Stretchy morph UI

This skill produces interfaces where every state change *morphs*: a tab indicator stretches like a worm on its way to the next tab, a button squeezes into a loading circle and swells back, a product picture lifts off its card, shrinks into a chip and drops into the cart. It was distilled from building a 23-component showcase (in `assets/showcase.html`) and the bugs and design corrections found along the way.

The look comes from one idea: **stretch is caused by something.** An element deforms because its parts disagree (one edge arrives before the other), because it is moving fast (it lengthens along its path), because it is being squeezed (it bulges the other way to keep its volume), or because it was just hit (it wobbles). Random wobble on a loop looks cheap; stretch with a cause looks like material.

## Step 0, every time: audit the user's code and confirm

Before building or editing anything, find out what in the user's own interface can become stretchy, and let them choose. Details, judgement criteria and message templates are in `references/audit.md`; the short version:

1. **Find the code**: pasted code, attached files (on claude.ai, list `/mnt/user-data/uploads`), the working directory or repo, an artifact link (read it with the artifact tool), or a source the user points to. If there is none, say what you looked for and offer two paths: share the code, or build something new from scratch.
2. **Scan it**: `python scripts/audit_ui.py <paths>` reports the stack, existing motion, missing reduced-motion handling, and candidates per UI category with `file:line`, each mapped to a showcase component and technique.
3. **Read every hit in context** and keep only real candidates. For each, note where it is, what happens now, the morph sentence it would become, effort (small, medium, large) and any risk (component library markup, an existing animation library, a native control whose mobile picker would be lost, very long lists).
4. **Prioritise** by visibility × frequency × fit, group duplicates (all buttons using one shared `Button` are one item), cap the list at about ten, and list anything you advise against with the reason.
5. **Ask for confirmation** in the user's language: the numbered proposals, then a question inviting them to pick numbers, take all recommended, or type extra parts they want stretchy that are not on the list. Use a tappable-choice tool if the environment has one, otherwise plain text. **End the turn there; make no edits before the reply.**
6. **Build what they chose** plus anything they added, then follow the Workflow below and report per item.

If the user already named the parts they want, still audit: put their parts first, offer the rest as optional, and keep the question short.

## Files

All paths are relative to this skill's folder (the folder containing this `SKILL.md`), not to the user's project. Resolve them against the skill folder when you read or run them.

| Path | What it is | When to open it |
|---|---|---|
| [`assets/stretchy-core.js`](assets/stretchy-core.js) | The spring engine plus helpers (edge pairs, segmented indicator, volume scale, bulging SVG edges, FLIP reorder, thrown objects) | Paste into every page you build. Read it once so you know the helpers. |
| [`assets/starter.html`](assets/starter.html) | Page skeleton: light/dark tokens, Thai-capable variable font, reduced-motion handling, the core inlined, one example component | Start a new page from it |
| [`assets/showcase.html`](assets/showcase.html) | All 23 working components from the original build. Each JS section starts with a banner like `/* ---------- tabs ---------- */` | When a request matches a catalog component, `grep -n "/\* ---------- " assets/showcase.html` and read just that section plus its CSS |
| [`references/audit.md`](references/audit.md) | How to find, scan, judge and prioritise the user's code, and the confirmation message templates (Thai and English) | At Step 0, every time |
| [`references/techniques.md`](references/techniques.md) | The 11 stretch techniques in depth, with code and tuning numbers | Before building anything you have not built before |
| [`references/components.md`](references/components.md) | Catalog: each component's recipe, spring values and gotchas | When the request names or resembles a catalog component |
| [`references/new-components.md`](references/new-components.md) | How to design a stretchy version of *any* component, plus 14 worked designs not in the showcase | Whenever the request is outside the catalog |
| [`scripts/audit_ui.py`](scripts/audit_ui.py) | Scanner for the user's code: stack, existing motion, and stretchy candidates with `file:line` | At Step 0, every time |
| [`scripts/check_page.py`](scripts/check_page.py) | Headless browser check: JS errors, sideways overflow on phone and desktop, invisible elements stealing clicks, and contact sheets of animation frames | After every build, before you hand anything over |

If a visual design skill is available (for example `frontend-design` or `ui-ux-pro-max`), read it too. That skill decides how the page looks (palette, type, layout); this one decides how it moves. Motion polish cannot rescue a generic-looking page.

## Workflow (after the user confirms)

1. **Write the morph sentence for each component.** "When *trigger*, *shape A* becomes *shape B*, and it stretches because *cause*." Example: "When a tab is clicked, the indicator moves to it, and it stretches because its leading edge is stiffer than its trailing edge." If you cannot fill in the cause, pick one from the table below. This sentence is the design; everything else is implementation.
2. **Pick the technique(s)** from the table. Most components use one primary stretch plus one small feedback wobble.
3. **Define resting states as numbers**: widths, heights, radii, positions, progress 0 to 1. Springs animate numbers and you write them to `style` in `onUpdate`. CSS transitions handle only colour and opacity (and short content crossfades).
4. **Plan the content.** Text and icons must not reflow or squash while the container morphs. Give each content state its own layer at its final size, anchored (usually centred), and crossfade: exit fast (≈150 ms), enter after a ≈100–150 ms delay with a slight scale or blur. The container's `overflow:hidden` reveals content as it grows.
5. **Build** from `assets/starter.html` with the core inlined. Write styles directly in spring callbacks; never trigger a framework re-render per frame.
6. **Accessibility and interruption pass** (checklist below).
7. **Test and look.** Run `scripts/check_page.py`, then capture frame contact sheets of the important interactions and actually look at them. The add-to-cart animation in the original build "worked" but looked cheap until frames were inspected; the fixes are in "Making it look good".

## Where the stretch comes from

| Situation | Technique (details in `references/techniques.md`) | Seen in |
|---|---|---|
| Something moves between slots | **Edge pair**: two springs for leading and trailing edges, leading one stiff, swapped by direction | Tabs, carousel dots, toggles, radio dot, stepper, dropdown highlight, rating capsule, sidebar nav |
| A container changes size or shape | **Split axes**: separate springs for width, height, radius with different stiffness, so one axis leads | Dynamic island, FAB to form, modal from button, dropdown, add-to-cart button |
| Something gets narrower or wider fast | **Volume preservation**: scale the other axis by velocity, `scaleY = clamp(1 − v/k)` | Send button, search field, dropdown width |
| Something travels fast | **Velocity stretch**: lengthen along the direction of motion, thin across it | Slider thumb, thrown cart item, carousel cards (skew), tooltip |
| A big surface moves | **Bulging edge**: draw the surface as an SVG path whose edge control point is offset by −velocity | Sidebar, bottom sheet |
| A part hangs off a moving part | **Lagging follower**: a softer spring chases the main one; use the gap for tilt or offset | Slider value bubble, accordion inner text |
| Feedback for a tap or arrival | **Kick**: add velocity to a spring resting at 0, it wobbles and settles | Checkbox, chips, cart, stars, badge, quantity limit shake |
| Blobs join or split | **Goo filter**: blur plus alpha threshold, sharp source composited on top | Goo menu |
| An element becomes a different element | **Container transform**: start at the trigger's rect, spring to the target rect, crossfade content | Modal, FAB, cart throw |
| The change needs a pause in between | **Sequenced morph through an intermediate shape** that carries meaning (spinner, check) | Send button, add-to-cart button |
| Dragging past a limit, or a list reorders | **Rubber band** (divide overscroll by ≈3) and **FLIP with springs** that keep velocity | Carousel, sheet, sorted product list |

## The engine in one paragraph

`Spring` is a damped harmonic oscillator integrated with semi-implicit Euler in 8 substeps per frame (frame delta capped at 1/30 s so a background tab cannot explode it). `to(target)` retargets **without resetting velocity**, which is what makes rapid clicks feel continuous instead of restarting. `set(x)` jumps without animation, `drag(x, v)` follows a pointer while recording velocity, `kick(v)` injects an impulse. Damping is multiplied by a global `bounce` factor at every tick, so one page-level control (soft 1.8, bouncy 1, stretchy 0.5) re-tunes every component live. Under `prefers-reduced-motion: reduce`, `to()` snaps to the target and fires `onRest` immediately, so logic that waits for an animation still runs.

Damping ratio ζ = c / (2√k). UI state changes feel right around ζ 0.6–0.8; playful feedback at 0.3–0.5; above 1 nothing overshoots. The presets used across the showcase:

| Role | k | c | Notes |
|---|---|---|---|
| Leading edge of an edge pair | 420–520 | 30–34 | Arrives first |
| Trailing edge | 140–170 | 17–19 | Lags, which creates the stretch |
| Container width (morph) | 240–320 | 18–24 | |
| Container height (morph) | 150–170 | 15–17 | Slower than width, so the shape stretches sideways first |
| Pointer follower (slider) | 650 | 42 | Tight, but still has velocity to read |
| Lagging follower (bubble) | 150 | 11 | Loose on purpose |
| Kick feedback | 380–420 | 12–16 | Kick with 6–10 |
| Height with visible overshoot (accordion) | 210 | 14 | |

## Rules of thumb

- **Cap every deformation.** Controls: volume preservation within ±7–15 %. Small fast things (a thrown chip, a slider thumb): up to 35–70 % stretch. Always clamp sizes to a positive minimum, since an underdamped spring can undershoot below zero.
- **Swap stiffness by direction.** In an edge pair, whichever edge faces the direction of travel gets the stiff spring. Without the swap, the indicator stretches correctly one way and compresses the other.
- **Opposite timing on the way back.** If width leads height when opening, let height lead width when closing. The shape then retraces a different path, which reads as elastic instead of a rewind.
- **Springs for state changes, time-based curves for paths whose shape matters.** A thrown object needs a predictable arc (quadratic Bézier, ease-in-out progress, around 800 ms). Independent x/y springs give wandering paths. Derive stretch from the frame-to-frame velocity either way.
- **Keep content upright.** To stretch something along an arbitrary direction without rotating its picture or text, use `rotate(a) scale(1+s, 1−s·0.45) rotate(−a)`.
- **One bold motion per component.** The rest of the component stays quiet: a colour change, a short fade.
- **Calm when idle.** Nothing wobbles on its own. At most one orchestrated moment on page load (the showcase opens the island once after 900 ms).

## Making it look good (lessons from the build)

The first add-to-cart version flew a plain coloured ball along two independent springs, shrank the button into an empty violet oval and squashed the cart. The user said it was not pretty. What fixed it generalises:

- **Move the real thing.** Clone the product picture, lift it slightly with a shadow, then shrink it into a round chip that still shows the picture while it flies. Abstract dots read as debug output.
- **Intermediate shapes must carry meaning.** A shrunken button is an empty blob unless it shows something: a spinner, a check that draws itself, a count. The add button now becomes a green circle with a check, then grows into the − n + stepper.
- **Subtle volume on controls.** A ±18 % vertical bulge on a button looked like a pill-shaped egg. ±7 % reads as soft material.
- **Arrival needs a receiver.** The cart icon dips and tilts, a ring pulses out, the badge pops. Something must visibly *catch* what was thrown.
- **Don't clip status marks.** A badge inside a morphing `overflow:hidden` pill gets cut off; put it in a wrapper outside the clip.
- **Don't repeat information.** The cart pill showed "3 ชิ้น 195 บาท" next to a badge saying 3. It now shows only the total.
- **Draw illustrations at a fixed aspect.** Percent-positioned CSS shapes inside a tile stretch when the tile widens. Use an inline SVG with a viewBox, centred in the tile.

## Accessibility and robustness checklist

- Respect reduced motion (the core does it; make sure CSS keyframes and transitions are also cut in a `prefers-reduced-motion` media query).
- Use real `button`, `input`, `role="switch"`, `role="tab"`, `role="slider"` etc. with the right `aria-*` state, updated in the same call that starts the animation.
- Content that is hidden by a morph gets `inert` (and must not intercept clicks: give invisible layers `pointer-events:none`, then switch it back on with the visible state).
- Move focus deliberately when the focused control disappears into a morph: to the replacement control, back to the trigger after a dialog closes, and only after the element is visible again (a `visibility:hidden` element cannot take focus).
- Keyboard paths: arrows for indicators, sliders, radios and listboxes; Esc closes overlays; Tab is trapped in modal dialogs.
- Announce results that are only visible as motion (`aria-live` status text: "ส่งแล้ว", "เพิ่มลงตะกร้าแล้ว").
- Measure after fonts load and on resize: register a resync function per component (`onResync` in the core) that `set()`s springs to freshly measured positions.

## Pitfalls that actually happened

| Symptom | Cause | Fix |
|---|---|---|
| Wide block children shrink-wrapped and centred | `place-items:center` on a `display:block` container now aligns block children in Chromium | Give block stages `place-items:normal` |
| Whole page scrolls sideways on phones | `grid-template-columns:1fr` lets a child's min-content (a carousel track) blow out the column | Use `minmax(0,1fr)` |
| Button could not be clicked | An invisible (opacity 0) sibling layer sat on top of it | `pointer-events:none` on hidden layers |
| Indicator lands in the wrong place on first paint | Measured before the web font loaded | Re-measure on `document.fonts.ready` and resize |
| Dot misaligned inside a `fieldset` | `legend` shifts the fieldset box in odd ways | Use a `div role="radiogroup"`, measure with `getBoundingClientRect` differences |
| Dialog lingered ~1 s after visibly closing | Rest threshold `eps` of 0.05 px is far stricter than the eye | Use `eps≈0.5` for pixel springs whose `onRest` triggers logic |
| Stepper "Next" button lost focus | Disabled while focused | Change its label/action instead of disabling, or move focus first |
| Slider broke after adding the date picker | Both declared `function setVal`; in one script the later declaration silently replaces the earlier | Prefix helpers per component (`dpText`), or wrap each component in its own block or module; check with `grep -oE "function [A-Za-z_]+" \| sort \| uniq -d` |
| A helper worked in the skill's starter but threw in a bigger page | The page never included it (`replayClass`) | Paste the whole core, or inline the two lines you need |

## Delivering

- For a standalone demo, build one self-contained HTML file (CSS and JS inline, the core pasted in). Load fonts from Google Fonts with a real fallback stack. Respect the host's dark/light handling. Then hand it over the way your host supports:
  - Claude (claude.ai or Claude Code with artifact publishing): publish the file as an artifact.
  - Antigravity: save the file in the workspace and open it in the built-in browser to watch the interactions. A browser recording is a good complement to the `check_page.py` contact sheets.
  - Anywhere else: save the file and tell the user its path.
- For a React, Vue or Svelte codebase, keep the core as a plain module. Create springs once (`useRef`/`onMounted`), write styles to element refs inside `onUpdate`, cancel on unmount, and keep component state (selected tab, count) in the framework while the spring only animates presentation. `references/new-components.md` ends with a React port of the worm tabs.
- Write UI copy in the user's language. If they write in Thai, the demo content is Thai, and a variable Thai-capable font such as Noto Sans Thai (with its width axis for condensed headlines) is a good default.
