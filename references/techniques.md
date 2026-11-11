# Stretch techniques

Eleven ways to make a transition stretch. Each one names its physical cause, shows the core code, gives the numbers that worked, and points to the showcase section that uses it (`grep -n "/\* ---------- name" assets/showcase.html`).

Contents
1. Edge pair (worm)
2. Split axes (anisotropic morph)
3. Volume preservation
4. Velocity stretch
5. Bulging edge (SVG surface)
6. Lagging follower
7. Kick (impulse wobble)
8. Goo filter
9. Container transform (shared element)
10. Sequenced morph through a meaningful intermediate
11. Rubber band and FLIP reorder
12. Content during a morph (applies to all)

---

## 1. Edge pair (worm)

**Cause:** the two ends of a moving thing have different stiffness, so the front arrives early and the back catches up.

Represent the moving element by its two edges, not by position and width. Animate each edge with its own spring; give the edge facing the direction of travel the stiff spring. Draw `left = L`, `width = R − L`.

```js
const ep = edgePair((L, R) => {
  ind.style.transform = `translateX(${L}px)`;
  ind.style.width = Math.max(0, R - L) + 'px';
});
ep.set(a, b);   // first paint, no animation
ep.to(a, b);    // later moves; edgePair picks which edge leads
```

- Leading k 420–520, c 30–34; trailing k 140–170, c 17–19.
- Works vertically too (top/bottom): sidebar nav highlight, dropdown highlight, radio dot.
- Works for anything shaped "between two points": a toggle knob (knob edges), a rating capsule (left edge fixed at star 1, right edge moves), a progress blob in a stepper (dot centre ± radius).
- Add a secondary deformation tied to the length: the toggle knob gets thinner as it gets longer (`height = K − (w − K)·0.3`), which reads as rubber.
- Keyboard and hover can drive it too: the dropdown highlight follows `pointerenter` and arrow keys, so it worms through the list.

Seen in: tabs, segmented controls, carousel dots, toggles, radio and checkbox, stepper, dropdown, rating, sidebar.

## 2. Split axes (anisotropic morph)

**Cause:** width and height respond at different speeds, so the shape stretches sideways before it grows down (or the reverse).

```js
const w = new Spring(126, { k: 240, c: 20, onUpdate: x => el.style.width  = Math.max(20, x) + 'px' });
const h = new Spring(37,  { k: 165, c: 16, onUpdate: x => el.style.height = Math.max(12, x) + 'px' });
const r = new Spring(19,  { k: 220, c: 20, onUpdate: x => el.style.borderRadius = Math.max(6, x) + 'px' });
function setState([W, H, R]) { w.to(W); h.to(H); r.to(R); }
```

- Opening: width leads (k ≈ 300), height lags (k ≈ 150). Closing: swap (height k ≈ 320, width k ≈ 150) so the shape retraces a different path.
- Clamp every dimension to a positive minimum; underdamped springs undershoot.
- Animate the radius as its own spring; a pill (radius = h/2) becoming a card (radius 24–40) looks best when the radius settles slightly before the size.
- Clamp target widths to the container (`Math.min(target, parent.clientWidth − 24)`) and re-measure on resize.

Seen in: hero island, FAB, modal, dropdown, add-to-cart button.

## 3. Volume preservation

**Cause:** squeezed material bulges the other way.

While width changes with velocity `v` (px/s), scale the other axis:

```js
const w = new Spring(200, { k: 260, c: 17, onUpdate: (x, v) => {
  el.style.width = x + 'px';
  el.style.transform = `scaleY(${volumeScale(v)})`;   // clamp(1 - v/9000, .93, 1.07)
}});
```

- Shrinking (v < 0) makes it taller; widening makes it flatter.
- Keep it subtle on controls (±7 %). The first add-to-cart version used ±18 % and the button looked like an egg.
- Apply as `transform`, never by changing the height property, so layout around it does not jump.
- Combine with centre anchoring (`left:50%; transform: translateX(-50%) scaleY(...)`) when the element should shrink toward its centre.

Seen in: send button, search field, add-to-cart button, dropdown width (inverted: grows taller, gets narrower).

## 4. Velocity stretch

**Cause:** fast things smear along their path.

For one axis (a slider thumb):

```js
const s = Math.min(.7, Math.abs(spring.v) / 2600);
thumb.style.transform = `translate(${x}px,-50%) translateX(-50%) scale(${1 + s},${1 - s * .42})`;
```

For any direction, keep the content upright:

```js
el.style.transform = `translate(${x}px,${y}px) translate(-50%,-50%) ${alongVelocity(vx, vy)}`;
// alongVelocity = rotate(a) scale(1+s, 1-s*.45) rotate(-a)
```

- Divide by 2500–3500 px/s; cap at 0.35 for pictures, 0.7 for plain shapes.
- Smooth the stretch (`st = st*.7 + target*.3`) when velocity comes from frame differences, or it flickers.
- For slides moving horizontally, a `skewX(−v/2500·7deg)` plus a small `scaleY` squash looks like jelly without making cards overlap. Keep `scaleX` growth under 3 % or neighbouring cards collide.
- Tooltips that slide between buttons: stretch them horizontally by their x-velocity while the width spring retargets to the new label.

Seen in: slider, carousel, tooltip, thrown cart chip.

## 5. Bulging edge (SVG surface)

**Cause:** a large surface's middle lags behind its anchored corners.

Draw the surface as an SVG path behind the content. Its moving edge is a quadratic curve whose control point is offset by the velocity:

```js
const sbW = new Spring(248, { k: 200, c: 17, onUpdate: (w, v) => {
  sb.style.width = w + 'px';
  svg.setAttribute('width', w + 70);                       // room for the bulge
  path.setAttribute('d', rightEdgePath(w, sb.clientHeight, edgeBulge(v)));  // clamp(-v*.05, ±56)
}});
```

- Sign: moving outward (v > 0) gives b < 0, so the middle lags (concave). Overshoot reverses it, so the edge wobbles flat.
- Bottom sheet: `topEdgePath(w, h, 28, clamp(-v*.035, ±36))`; extend the path 40–60 px below the bottom so an upward overshoot never reveals a gap.
- Put the SVG at `z-index:-1` inside the surface (which has its own stacking context) and make it `overflow:visible`.
- Drive it from drag velocity as well (`spring.drag(y, v)`), so the edge bends while the user drags.

Seen in: sidebar, bottom sheet.

## 6. Lagging follower

**Cause:** something attached loosely trails what it hangs from.

Run a second, softer spring toward the same target and use the gap:

```js
const main = new Spring(0, { k: 650, c: 42, onUpdate: draw });   // thumb
const lag  = new Spring(0, { k: 150, c: 11, onUpdate: draw });   // phantom
// rotate the bubble by the gap: inverted pendulum anchored at the thumb
const tilt = clamp((lag.x - main.x) * .7, -32, 32);
```

- Anchor the follower to the main element's position and use the gap only for rotation or offset; otherwise it drifts away visibly.
- Inner content of an expanding panel: `translateY(clamp(-v*.012, ±10))` gives a "contents shaken in a box" feel.

Seen in: slider value bubble, accordion.

## 7. Kick (impulse wobble)

**Cause:** something was hit, so it rings.

```js
const q = new Spring(0, { k: 420, c: 14, eps: .001,
  onUpdate: s => box.style.transform = `scale(${1 + s * .22},${1 - s * .22})` });
input.addEventListener('change', () => q.kick(input.checked ? 7 : -7));
```

- The spring rests at 0 and returns to 0; the sign of the kick picks which way it squashes first.
- Stagger kicks across siblings (`setTimeout(…, i*55)`) for a ripple (rating stars).
- "Can't do that" feedback: kick a translateX spring (k 600, c 12) for a head-shake, or kick the width spring for a bulge.
- `transform-origin` decides where it stretches from: quantity stepper uses `left center` for + and `right center` for −, so it stretches toward the side pressed.

Seen in: checkbox, chips, quantity, stars, cart, badge, send button success.

## 8. Goo filter

**Cause:** blobs of liquid merge when close and split when pulled apart.

```html
<filter id="goo">
  <feGaussianBlur in="SourceGraphic" stdDeviation="10" result="b"/>
  <feColorMatrix in="b" mode="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 22 -10" result="g"/>
  <feComposite in="SourceGraphic" in2="g" operator="atop"/>
</filter>
```

Apply `filter:url(#goo)` to a container of same-coloured blobs. The composite keeps icons sharp. Move blobs with a 0..1 progress spring each, staggered by 60–70 ms; reverse the stagger when closing.

- Keep shadows and borders off the blobs, they turn to mud.
- Focus outlines inside the filter get distorted; acceptable for small menus, otherwise draw focus rings outside the filtered layer.

Seen in: goo menu.

## 9. Container transform (shared element)

**Cause:** the thing you touched *becomes* the next thing.

1. Measure the trigger (`getBoundingClientRect`), `set()` the x, y, w, h, radius springs to it, show the overlay element there and hide the trigger (`visibility:hidden`).
2. Measure the target size (lay out the content at its final width first) and `to()` the springs.
3. Colour crossfade on the container (trigger colour → surface), trigger label fades out, final content fades in after ≈150 ms.
4. Closing: springs back to the trigger's *current* rect, swap stiffness so the return path differs, and only when all springs rest (`onRest` checking every spring's `raf`), hide the overlay, show the trigger and focus it.

- Use `eps ≈ 0.5` on these springs or the overlay lingers for a second after it looks done.
- On resize while open, `set()` to the new centred rect.

Seen in: modal, FAB to form.

The thrown-object variant (`throwTo` in the core) is a one-way container transform along an arc: the clone lifts (scale 1.08 and −12 px over the first 14 %), shrinks with ease-out toward a round chip, follows a quadratic Bézier whose control point is ≈90 px above the higher endpoint, with ease-in-out progress over ≈800 ms. Use time-based motion here because the path's shape matters; springs on x and y separately produce paths that wander.

## 10. Sequenced morph through a meaningful intermediate

**Cause:** the control is doing something in between (working, confirming).

Send button: pill → circle with spinner (width spring to 56, label fades) → circle turns green and a check draws (stroke-dashoffset) with a width kick → pill again.

Add to cart: violet pill → green circle with a self-drawing check (≈600 ms) → grows into the − n + stepper whose buttons ride the edges as it widens. Back to zero: stepper → empty circle (220 ms) → violet pill with the label fading in.

- The intermediate must show something; an empty shrunken shape looks broken.
- Lock all inner controls (`inert`) during the sequence, re-enable the destination's controls when it starts growing, and move focus to the control that replaced the focused one.

## 11. Rubber band and FLIP reorder

Rubber band: while dragging past a limit, apply only a third of the overscroll (`o > 0 ? o*.35 : …`). On release, project the position with velocity (`x + v*.18`), snap to the nearest slot and hand the release velocity to the spring (`spring.v = v; spring.to(slot)`), so the throw continues into the settle. Treat a release more than ≈90 ms after the last move as velocity 0.

FLIP with springs (`flipReorder` in the core): record tops, reorder the DOM, set each item's spring to `current + (oldTop − newTop)` with its existing velocity, and spring to 0. Stretch items vertically by speed. Because velocity carries over, a second reorder mid-flight stays smooth.

## 12. Content during a morph

Applies to every technique:

- Content does not reflow while the container changes size. Lay each content state out at its final size in its own absolutely positioned layer, anchored where it should grow from (usually centre or the anchored corner), and let `overflow:hidden` on the container reveal it.
- Exit fast (opacity ≈150 ms, optionally blur 6 px and scale .9), enter late (delay ≈100–150 ms, 250–450 ms with a slight overshoot curve such as `cubic-bezier(.3,1.5,.5,1)`).
- Stagger multiple pieces of content by 35–50 ms in reading order (sidebar labels, search suggestions). Remove the delay when hiding.
- Controls that ride a growing container (stepper − and +) are positioned against its edges, so they travel with the stretch for free.
- Text inside a velocity-stretched object stays readable only if the stretch is small or the object is moving too fast to read anyway.
