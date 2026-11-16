# Core API (assets/stretchy-core.js)

Read this instead of the core. Names below are globals in a plain script (`assets/starter.html`) and named exports of the module from `python scripts/add_core.py --module <dest.js>`. Open the core only to change the engine.

## Spring

```
new Spring(x0, { k = 220, c = 18, eps = 0.05, onUpdate(x, v), onRest() })
```

- `.to(target, { k, c }?)` retargets, keeps velocity (interruptible). Passing `k` / `c` changes them for later calls too. Returns the spring.
- `.set(x)` jumps with no animation: calls `onUpdate(x, 0)`, never `onRest`.
- `.drag(x, v)` follows a pointer: sets position and target to `x`, records velocity `v`, so a later `.to()` continues the throw.
- `.kick(v)` adds an impulse and lets it ring back to the target (does nothing under reduced motion).
- `.stop()` halts where it is, keeping `x`, `v` and the target (teardown).
- Fields: `.x` position, `.v` velocity (units per second), `.t` target, `.k`, `.c`; `.raf` is truthy while animating (ask "still moving?", e.g. in an `onRest` waiting on several springs).
- Units are yours (px, 0..1, degrees). Pick `eps` to match: `0.05` for px springs that only draw, about `0.5` for px springs whose `onRest` triggers logic, `0.001` for 0..1 springs.
- Reduced motion (`RM.matches`): `.to()` snaps to the target and calls `onRest` synchronously, so set your state first.
- `bounce` is a global damping multiplier read on every tick; `setBounce(x)` sets it: 1.8 soft, 1 bouncy, 0.5 very stretchy. It re-tunes running animations too.
- Integration: semi-implicit Euler in 8 substeps per frame, with the frame delta capped at 1/30 s so a background tab cannot explode it.

## Helpers

| Call | Does | Returns |
|---|---|---|
| `edgePair(draw(L, R), { fast = {k:420,c:30}, slow = {k:150,c:18} })` | Two edge springs for a shape moving between slots; the edge facing travel gets `fast`. | `{ set(a, b), to(a, b), stop() }`: `set` for first paint and resync, `to` for moves. Works for left/right or top/bottom. |
| `makeSegmented(root, { attr = 'aria-pressed', initial = 0, onChange(i, btn) })` | Segmented control or tab bar with a worm indicator. Markup `<div class="seg"><span class="seg-ind"></span><button data-seg>…</button>…</div>`; root `position:relative`, indicator absolute at `left:0`. Sets `attr` on buttons (`attr: 'aria-selected'` also manages roving `tabIndex`); ArrowLeft/Right. Class `on` is added only once the indicator covers the button. | `{ select(i, anim = true, notify = true), index, destroy() }` (removes listeners, stops springs, leaves the current inline styles) |
| `makeAccordion(root, { single, initial = [], gap = 0, squash = true, onChange(openIndexes) })` | Elastic accordion over direct children: `<details>` (enhanced in place; content wrapped in `.acc-panel > .acc-in`; a `name` group becomes single mode) or `.acc-item > button.acc-btn[aria-controls] + .acc-panel > .acc-in`. `single` defaults true (false for `<details>` without `name`); `initial`: index or array; `gap`: px an opened card moves from its neighbours; chevron: `[data-acc-chev]` or an `svg` in the header. | `{ open(i), close(i), toggle(i), openIndexes, single (get/set), destroy() }` (removes listeners, stops springs, leaves the current inline styles) |
| `onResync(f)` | Runs `f` on window resize and after fonts load (re-measure, `set()` springs there). `resyncAll()` runs them all now. | A function that unregisters `f` |
| `volumeScale(v, k = 9000, lo = 0.93, hi = 1.07)` | Volume preservation: other-axis scale while a width changes at velocity `v` (px/s). | number |
| `alongVelocity(vx, vy, { max = 0.35, div = 3400, thin = 0.45 })` | Stretch along travel, content kept upright. | transform fragment (`''` below 40 px/s) |
| `edgeBulge(v, k = 0.05, max = 56)` | Control-point offset for a bulging edge. | number |
| `rightEdgePath(w, h, b)` | Surface anchored left, moving right edge (sidebar). | SVG path string |
| `topEdgePath(w, h, r, b, extra = 60)` | Surface anchored bottom, moving top edge, rounded corners (sheet). `extra` extends below so an upward overshoot never shows a gap. | SVG path string |
| `flipReorder(els, mutate)` | FLIP reorder; springs keep velocity, items stretch vertically while moving. `mutate()` reorders the DOM. | nothing |
| `throwTo({ container, fromEl, toEl, background = 'transparent', duration = 800, arc = 90, endSize = 30, startRadius = 20, pad = 20, onArrive })` | Clone of `fromEl` shrinks to a round chip and is thrown along an arc into `toEl`. `container` must be `position:relative` and contain both. Reduced motion: only `onArrive` runs. | nothing |
| `replayClass(el, cls)` | Restarts a CSS keyframe animation. | nothing |
| `$(sel, root = document)`, `$$(sel, root = document)`, `clamp(v, a, b)`, `lerp(a, b, t)`, `RM` | Query helpers, clamp, lerp, reduced-motion query. | element or array / number / media query list |

## Spring presets

Damping ratio ζ = c / (2√k). UI state changes feel right around ζ 0.6–0.8; playful feedback at 0.3–0.5; above 1 nothing overshoots.

| Role | k | c | Notes |
|---|---|---|---|
| Leading edge of an edge pair | 420–520 | 30–34 | Arrives first |
| Trailing edge | 140–170 | 17–19 | Lags; creates the stretch |
| Container width (morph) | 240–320 | 18–24 | |
| Container height (morph) | 150–170 | 15–17 | Slower than width: stretches sideways first |
| Pointer follower (slider) | 650 | 42 | Tight, velocity still readable |
| Lagging follower (bubble) | 150 | 11 | Loose on purpose |
| Kick feedback | 380–420 | 12–16 | Kick with 6–10 |
| Height with visible overshoot (accordion) | 210 | 14 | |
| Height closing to 0 (accordion) | 260 | 30 | Plus a floor at 0 (`techniques.md`, section 7) |

## Runtime cost rules

- A spring runs only while moving and stops at rest: nothing ticks on an idle page.
- Never read layout inside `onUpdate` (`offsetWidth`, `clientHeight`, `getBoundingClientRect`): it forces a reflow per frame. Measure once, cache the number, refresh it in `onResync` or a `ResizeObserver`.
- Prefer `transform` and `opacity`. Springs that write `width` or `height` (indicators, morphing containers, accordion panels) lay out every frame: keep them small or absolutely positioned, and keep heavy content out of the reflowing subtree.
- Lists with hundreds of rows: no spring per row. Animate one shared indicator, or only the rows in view.
- No `will-change` on resting elements; add it only when a performance trace shows a need.
- Single-page apps: on unmount call `destroy()` (`makeSegmented`, `makeAccordion`), `stop()` (springs, edge pairs) and the function `onResync` returned.
- Importing the module on a server is safe (no DOM access at load); create springs in mount hooks.
