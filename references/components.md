# Component catalog

The 24 components in `assets/showcase.html`. For each: the morph sentence, the techniques, the numbers, and the gotchas found while building it. To reuse one, read its JS section (banner in brackets) and the matching CSS block (CSS comments use the same names).

| # | Component | Banner |
|---|---|---|
| 1 | Dynamic island | `hero island` |
| 2 | Worm tab bar | `tabs` |
| 3 | Checkout stepper | `stepper` |
| 4 | Collapsible sidebar | `sidebar` |
| 5 | Jelly carousel | `carousel` |
| 6 | Send button to loader | `send button` |
| 7 | Stretchy switch | `toggles` |
| 8 | Liquid radio and squash checkbox | `radio and checkbox` |
| 9 | Filter chips | `chips` |
| 10 | Search that bursts from its icon | `search` |
| 11 | Dropdown that pours from its button | `dropdown` |
| 12 | Velocity slider with pendulum bubble | `slider` |
| 13 | Quantity stepper | `quantity` |
| 14 | Star rating with capsule | `rating` |
| 15 | Add to cart throw | `add to cart` |
| 16 | Goo menu | `goo menu` |
| 17 | Modal from button | `modal` |
| 18 | Toasts that sprout from a dot | `toast` |
| 19 | Travelling tooltip | `tooltip` |
| 20 | Jelly bottom sheet | `bottom sheet` |
| 21 | FAB that spreads into a form | `fab` |
| 22 | Elastic accordion | `accordion` |
| 23 | Date picker, single day or range | `date picker` |
| 24 | Choice chips (single-select chip radio) | `choice chips` |

Also global: a segmented "ความเด้ง" control sets `bounce` to 1.8 / 1 / 0.5.

---

**1. Dynamic island.** When the state changes (idle, music, timer, call), the black pill becomes a new size and radius, and it stretches because width (k 240) leads height (k 165). Content panes are fixed to each state's size, centred at the top, crossfading with blur. Sizes `[w,h,r]`: idle 126×37 r19, music 340×76 r30, timer 204×40 r20, call 360×168 r42; clamp width to container − 24. One intro morph 900 ms after load. Timer counts for real only while visible.

**2. Worm tab bar.** When a tab is chosen, the indicator moves, stretching because of an edge pair. Content above crossfades with a token to ignore stale timeouts on rapid clicks. `role=tablist`, roving tabindex, arrow keys.

**3. Checkout stepper.** When moving to the next step, a violet blob behind the current dot travels (edge pair around the dot centre ± 22) and the progress line fills with an overshooting spring (k 190, c 14, clamped 0..1). Completed dots pop into checks (CSS keyframe). Rail positioned from first to last dot centre, re-measured on resize. On the last step the Next button becomes "เริ่มใหม่" instead of being disabled (a disabled focused button drops focus).

**4. Collapsible sidebar.** When toggled, the width springs 248 ↔ 76 and the right edge, drawn as an SVG path, bulges with `−v·0.05` (±56). Labels fade out at once and stagger back in (40 ms each). The inbox badge morphs from a 22 px count to a 10 px dot at the icon corner. Nav highlight is a vertical edge pair. Main content padding follows the width on wide screens; under 600 px the sidebar overlays instead and closes on selection, on Esc, or when the content is tapped.

**5. Jelly carousel.** Track position is one spring (k 200, c 22). Slides skew by velocity (`skewX(−v/2500·7°)`) and squash slightly; gap 24 px keeps them from colliding. Drag with rubber banding at both ends; release projects with velocity × 0.18. Dots use an edge-pair worm. Inactive slides get `aria-hidden`.

**6. Send button.** Click: label fades, width springs 200 → 56 with volume preservation, spinner shows; after 1.5 s it turns green, a check draws, and a width kick (+700) makes it pop; after 3.4 s it springs back. `aria-busy` plus a live status line ("กำลังส่ง…", "ส่งแล้ว"). Ignore clicks while busy.

**7. Stretchy switch.** Knob is an edge pair (fast k 520 c 34, slow k 170 c 19) between `[4,30]` and `[30,56]` in a 60×34 track; knob height shrinks as it stretches (`26 − (w−26)·0.3`). `role=switch` with `aria-checked`. The dark-mode switch writes `data-theme` on `<html>`; its initial state reads `prefers-color-scheme`.

**8. Liquid radio, squash checkbox.** A single 12 px dot flows between radio rings as a vertical edge pair (fast k 460). Measure ring centres with `getBoundingClientRect` differences against the group (a `fieldset/legend` breaks offset maths, so use `div role=radiogroup`). Native inputs stay in the DOM, visually hidden, so arrow keys work. Checkbox box kicks a squash spring on change; the check is a stroke-dashoffset draw.

**9. Filter chips.** Selecting a chip springs its check icon slot from 0 to 20 px wide (k 320, c 15) with the icon scaling in, so the chip swells and neighbours reflow around it; plus a squash kick. A live line updates the result count.

**10. Search.** A 52 px round icon button springs to `min(340, container − 8)` wide with volume preservation; the input fades in after 120 ms; the close button pops in with an overshoot curve. Suggestion chips stagger up (50 ms). Hidden close button needs `pointer-events:none`, otherwise it covers the icon button when collapsed (this bug shipped once).

**11. Dropdown.** The container's height springs from 52 to 52 + list height (k 210, c 15); its width narrows by up to 6 % with the height velocity (inverse volume). The highlight is a vertical edge pair following hover and arrow keys (listbox with `aria-activedescendant`). Selecting re-sorts the product list below with `flipReorder`. Closes on outside pointerdown, Esc, Tab.

**12. Velocity slider.** Thumb follows the pointer through a tight spring (k 650, c 42) and stretches by its velocity (`/2600`, cap .7). The value bubble scales in on press and tilts by the gap to a loose phantom spring (k 150, c 11). Arrow/Home/End keys show the bubble briefly. `touch-action:none`, pointer capture.

**13. Quantity stepper.** + and − kick a scale spring with `transform-origin` on the opposite side, so the pill stretches toward the button pressed. Digits roll: old number slides out, new one in from the direction of change (progress spring 0 → 1). At the limits, a translateX kick shakes the pill instead.

**14. Star rating.** A capsule behind the stars is an edge pair from star 1's left edge to star n's right edge; it follows hover previews and snaps back on pointerleave. Clicking pops stars 1..n with staggered kicks. `role=radiogroup`, each star `role=radio`, arrow keys.

**15. Add to cart.** See technique 9 (throw) and 10 (sequenced morph). The product picture is an inline SVG at a fixed aspect, cloned for the throw (strip its inline `style` first, it may hold a mid-animation transform). On arrival: re-render the cart, kick the cart pill squash, dip and tilt the cart icon, pop the badge, replay a ring pulse. Badge lives outside the clipped pill. Pill text shows only the total (the badge already shows the count). Free-shipping note turns green at the threshold. Logical quantity updates on click; the cart display updates on arrival.

**16. Goo menu.** Three items fan out at −150°, −90°, −30° (radius 96) on 0..1 springs with 70 ms stagger, merged by the goo filter. Main button rotates its plus by 135° with an overshoot curve. Hidden items `tabindex=-1`.

**17. Modal from button.** Container transform from the delete button to a centred dialog (width k 260, height k 150 opening; reversed closing). Background fades from the button's pink to the surface colour. Scrim, Esc, Tab trap, focus back to the trigger once the overlay hides.

**18. Toasts.** Each starts as a 48 px circle (icon only) rising from below, then its width springs to full while the text fades in; older toasts move up 58 px each with their own y springs. Auto-dismiss at 3.8 s: shrink back to a circle, drop 24 px, blur out. Max three; tap to dismiss. Each toast is `role=status`.

**19. Travelling tooltip.** One tooltip for the whole toolbar: x spring (k 320) moves between buttons, width spring fits the new label (measured in a hidden span), scale spring shows/hides with a 140 ms grace period, and it stretches by x-velocity. First appearance `set()`s position so it doesn't fly in from the last place. Toolbar buttons are real toggles (`aria-pressed`) that format the sample text.

**20. Jelly bottom sheet.** Sheet y spring (k 230, c 22); the top edge is an SVG path bulging with `−v·0.035`. Dragging the handle uses `spring.drag` (rubber band above the top); release closes if v > 500 px/s or it is past 40 % of its height, carrying the release velocity. Scrim opacity follows y. `role=dialog`, `inert` when closed, Esc closes.

**21. FAB to form.** Width (k 320) leads height (k 150) opening; height leads width closing. The form inside is laid out at its final size anchored bottom-right and fades in after 160 ms. Saving prepends a note that pops in. Esc closes; focus moves to the textarea, then back to the FAB.

**22. Elastic accordion** (`makeAccordion` in the core). When a question is opened, its panel's height overshoots and settles, and it stretches because the height spring is underdamped (k 210, c 14) while the content inside lags by `−v·0.012` (±10 px) like something shaken in a box. Small companions, all capped so the overshoot stays the hero: the opened card drifts 6 px away from its neighbours (`gap`, a 0..1 spring k 260 c 18 driving its margins); every card below a moving panel squashes by the summed height velocity above it (`scale(1+y/2, 1−y)`, `y = v/30000` clamped ±4 %, origin top; peaks measured at 1.9 % desktop, 2.6 % phone); the chevron flips on a rotation spring (k 300, c 15) plus a squash kick (+7 opening, −5 closing). Closing uses a firmer spring (k 260, c 30) **and lands on a floor**: when a closing panel reaches 0 moving downward, its x and v are zeroed, because at bounce 0.5 any spring to 0 rings through 0 and the panel would reopen a few pixels. The showcase is plain `<details name="faq">` (opens without JS); the helper wraps each item's content in `.acc-panel > .acc-in` (`display:flow-root`, so child margins are measured), removes `name` (the browser would otherwise close siblings instantly, with no animation) and treats it as single mode, calls `preventDefault` on the summary click and keeps `open` until the close spring rests, and listens to `toggle` so find-in-page, `#hash` and scripts that set `open` animate too (it remembers the value it set itself, so its own changes are not mistaken for external ones). The re-parenting is for plain, server-rendered or CMS HTML; for framework-rendered markup, render `.acc-panel > .acc-in` inside each `<details>` yourself (an existing panel is used as is), don't bind `open`, and call the helper once on mount (no teardown), or port it like the React worm tabs. Also accepts `.acc-item > button.acc-btn[aria-controls] + .acc-panel > .acc-in` markup, with `aria-expanded` kept in sync. A worm segmented control switches ทีละข้อ / หลายข้อ (`faq.single = …`, which closes extras). Panels are `inert` while closed; ArrowUp/Down (wrapping), Home, End move focus between headers and are ignored inside panel content. A `ResizeObserver` on each `.acc-in` re-measures open panels when width or content changes. Size the stage for *all* items open at 390 px (the showcase uses 560 px, 620 px under 600 px) so switching modes never moves the page.

**23. Date picker (single day or range).** A worm segmented control switches mode. *Single:* the selection blob is two edge pairs, one per axis (x fast k 480 / slow 190, y fast 480 / slow 230), so a diagonal jump stretches it into a liquid blob before it settles into a circle; the blob appears with a scale spring (k 380, c 19). *Range:* first tap sets an anchor blob, then a second blob follows hover and arrow-key focus while one capsule per week row (each an edge pair) fills the range: rows after the anchor row pour in from the left, rows before it from the right, the anchor row grows out of the anchor cell, each delayed 40 ms per row of distance; capsules fade with width (`opacity = w/24`) and are dimmed while previewing; the second tap commits, and taps before the anchor simply make it the start. Blobs keep their identity (anchor stays blob A) so they never swap places on commit. *Month change:* the old grid is cloned (ids stripped, `inert`) and both grids slide by one spring with `skewX` from velocity; blobs and capsules are `set()` for the new month so they ride in with it. *Summary card:* rows container springs 64 → 128 px between modes; a vertical edge-pair highlight sits on the field being picked and stretches over both rows when the range is complete. Day numbers on a blob turn white after a 100 ms delay so they don't vanish against the light background before the blob arrives. Thai dates use `Intl.DateTimeFormat('th-TH', {…, timeZone:'UTC'})` on UTC day numbers (Buddhist year, no time-zone drift). Keys: arrows ±1/±7 days, Home/End week, PageUp/PageDown month; moving past the month edge changes month and refocuses. Adjacent-month days are shown muted and disabled.

**24. Choice chips (single-select chip radio).** When a chip is picked, one filled capsule travels from the old chip to the new one, and it stretches because each axis is an edge pair whose leading edge is stiff (x fast k 460 c 31 / slow 170 c 19; y fast 460 c 31 / slow 210 c 22), so a hop to the neighbouring chip stretches it about 35 % longer and a jump to another wrapped row also stretches it about 35 % taller, a diagonal liquid blob. Radius is `min(w,h)/2` every frame. Paint order does the look: the container has `isolation:isolate`, each chip's surface is a `::before` at `z-index:-2`, the blob is at `-1`, only labels and icons paint above (the border lives on the `::before` with the surface, or it rings the blob), so the blob visibly passes *over* the chips in between but under their text (like the tab worm). **The target must stand still.** The picked chip grows a check slot (0 → 20 px, k 320 c 15, plus a .3× gap) while its side padding shrinks by .65× the slot (29 px at rest), so every chip keeps its outer width. An earlier version let the chip grow, which re-centred both wrapped rows: every chip slid sideways and wobbled with the slot spring, and the blob chased a moving target for about 0.8 s. Constant width means the blob is aimed once per selection, with no per-frame re-aim. Measure the target with `getBoundingClientRect()` relative to the container, not `offsetLeft`/`offsetWidth`, which round to integers: centred rows sit on sub-pixel positions, so the integer rect left a hairline of the white surface at rest. **Fill the chip when the blob lands.** The slow trailing edge (ζ ≈ .73) overshoots back inside the chip after arriving, which uncovered a 2 to 8 px white sliver for about 250 ms. On the first frame the blob covers the target (each edge within 3 px), the chip gets `.cc-on`, which makes its own surface violet and its label white. From then on the rebound merges into the chip, and the label turns white exactly when the blob arrives instead of after a guessed delay. Semantics: `role="radiogroup"` with `button role="radio" aria-checked`, roving `tabindex`, arrows (both axes) move *and* select with wrap, Home/End, an `aria-live` line updated only on user changes (not on init). Use a class other than the filter chips' `.chip`, which the filter-chip JS selects page-wide. Under reduced motion the check slot needs `transition:none!important` (see the pitfall in SKILL.md). **Porting:** keep the `.cc-on` timing and the three-layer paint order; a port that bound the selected style to `aria-checked` and kept `background` on the chips made the picked chip vanish mid-flight and hid the capsule behind the others (SKILL.md, "Moving indicators").
