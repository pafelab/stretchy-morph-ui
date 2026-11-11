# Designing a stretchy version of any component

The catalog covers 24 components, but the method generalises. This file gives the method, 14 worked designs for components that are *not* in the showcase, and a React port pattern.

## The method

1. **List the state changes and their triggers.** Open/close, select, add/remove, drag, success/error, arrive/leave.
2. **Find the moving parts** in each change: what travels, what resizes, what appears, what gets touched, what receives something.
3. **Ask the cause questions for each part.** Each "yes" names a technique from `techniques.md`:

   | Question | Technique |
   |---|---|
   | Does it travel between known slots? | Edge pair |
   | Does it travel freely or fast (drag, throw)? | Velocity stretch |
   | Does it change size or shape? | Split axes, plus volume preservation if it narrows or widens quickly |
   | Is it a large surface sliding in? | Bulging SVG edge |
   | Does something hang off it or sit inside it? | Lagging follower |
   | Is it tapped, or does it receive something? | Kick |
   | Does it become a different element? | Container transform (or throw, if it flies elsewhere) |
   | Is there waiting or confirming in between? | Sequenced morph with a meaningful intermediate |
   | Can it be dragged past a limit, or do siblings move to make room? | Rubber band, FLIP with springs |
   | Do several blobs join or split? | Goo filter |

4. **Choose one hero stretch per component.** Everything else gets a small kick, a fade or a colour change. Two big stretches at once compete and read as chaos.
5. **Write the numbers.** Resting states (sizes, radii, positions, 0..1 progress) and springs from the preset table in SKILL.md. Decide deformation caps.
6. **Plan content.** What is visible in each state, how it is anchored, which layer fades when.
7. **Plan access.** Native element or ARIA role, state attributes, keyboard, focus after the morph, live text for anything only shown by motion, `inert` on hidden layers.
8. **Build, check, look, tune.** Run `scripts/check_page.py`, capture frames of the hero interaction, fix whatever looks like debug output.

## Worked designs

### Hamburger menu that becomes a close button, then a panel
- Sentence: when tapped, the three bars fold into an X and the button grows into the menu panel, stretching because the middle bar's ends collapse toward its centre at different speeds and the panel's width leads its height.
- Middle bar: edge pair shrinking to its centre point (fast/slow edges), opacity out at the end. Top and bottom bars: rotation spring to ±45° plus a length kick so they overshoot slightly.
- Panel: container transform from the button rect (width k 300, height k 150), links stagger in 40 ms apart.
- Access: `aria-expanded`, `aria-controls`, Esc closes, focus first link, return focus to the button.

### Pull to refresh
- Sentence: as the list is pulled down, a blob hanging from the top stretches with the pull, and at the threshold it snaps free into a round spinner.
- Pull distance with rubber banding (`d^0.8` or `d·0.4` past 80 px). Draw the blob as an SVG path: a neck whose width shrinks as pull grows (`neck = lerp(40, 8, pull/threshold)`) ending in a circle. Past the threshold, kick a scale spring on the circle and hide the neck (it "snaps").
- Release: spring the spinner to its resting slot carrying the release velocity; on finish, shrink-kick it out and spring the list back.
- Access: a visible "รีเฟรช" button as an alternative; live text "อัปเดตแล้ว".

### Swipe to delete
- Sentence: as a row is dragged left it skews with its speed, the red action behind it grows, and when released past the threshold the row flies off and the gap closes elastically.
- Row x: `spring.drag(x, v)`; skew `−v/3000·6°`. Action icon: kick when crossing the threshold (haptic-like cue).
- Release past 40 % or v < −600: spring x to −width with the release velocity, then collapse height with an overshooting height spring (k 210, c 14) and `flipReorder` the rows below.
- Access: a delete button in each row (keyboard path), "ลบแล้ว" with an undo toast.

### Like button
- Sentence: pressing squashes the heart, releasing launches it taller than normal before it settles, and the count rolls up.
- Press: kick a squash spring negative (wide and flat). Release: kick positive. Fill colour crossfades. A ring pulse (`replayClass`). Count digits roll as in the quantity stepper.
- Access: `aria-pressed`, label includes the count.

### Two-thumb range slider
- Sentence: each thumb stretches with its own speed, and the selected range between them trails slightly behind them.
- Each thumb: tight follower spring + velocity stretch. The fill is an edge pair whose targets are the thumb positions, using softer springs, so it visibly lags on quick drags.
- Thumbs meeting: clamp, and kick both toward each other's opposite side for a bump.
- Access: two `role=slider` elements with `aria-valuemin/max/now` constrained by each other.

### Drag to reorder list
- Sentence: the picked-up item follows the finger, tilting with its sideways speed, while the others slide apart to open a gap and settle with a little stretch.
- Picked item: tight x/y springs to the pointer, `scale(1.04)` and a shadow, tilt from a lagging phantom on x (`rotate(clamp(gap·0.3, ±8)°)`).
- Others: compute the target index, apply `flipReorder` on index change. Drop: spring the item into its slot carrying velocity.
- Access: keyboard reorder (Space to pick up, arrows to move, live text "ย้ายไปลำดับที่ 3").

### Floating-label text field
- Sentence: on focus the label floats up and shrinks, and the underline grows outward from exactly where you clicked.
- Label: progress spring 0..1 driving `translateY` and `scale`. Underline: edge pair starting collapsed at the click x (or centre for keyboard focus) and expanding to 0 and full width.
- Error: translateX kick for a head-shake, colour to danger, message fades in below.
- Access: a real `label for`, `aria-invalid`, `aria-describedby` to the message.

### OTP / PIN code input
- Sentence: the highlight box worms from cell to cell as you type, each digit pops in, and a wrong code shakes the whole row.
- Highlight: edge pair across cells. Digit: kick scale on input. Wrong: translateX kick on the row plus red tint; correct: cells turn green in a staggered wave of kicks.
- Access: one real input with `autocomplete="one-time-code"` (render the cells from its value), or six inputs with paste handling.

### Upload progress ring that becomes a check
- Sentence: the ring fills with an elastic lead and, when finished, collapses into a check mark.
- Ring: `stroke-dashoffset` from a spring that chases real progress (overshoot clamped to 100 %). Stroke width swells with the progress velocity (volume). Done: sequenced morph, the ring shrinks to a dot with a split-axes spring, then the check draws.
- Access: `role=progressbar` with `aria-valuenow`, live text at completion.

### Card that becomes the detail page (shared element transition)
- Sentence: the tapped card lifts and grows into the page header while its neighbours drift away.
- Container transform at page level (fixed overlay) from the card rect to the header rect; the image keeps aspect via `object-fit:cover` while the box morphs. Neighbours: staggered opacity and a small translate away from the tapped card. Back reverses with swapped stiffness.
- Access: real navigation (history push), focus the page heading after the morph.

### Notification bell with popover
- Sentence: a new notification rings the bell like a pendulum, and opening it pours the panel out of the bell.
- Bell: rotation spring with `transform-origin: top center`, kicked ±; badge pops with a kick. Panel: container transform from the bell (width leads), items stagger, unread dots kick.
- Access: `aria-expanded`, count in the label, Esc closes.

### Grid ↔ list view switcher
- Sentence: switching views morphs every item from tile to row at once, each stretching as it moves to its new place.
- Switcher: worm segmented control. Items: record rects, switch the layout class, then spring each item's translate and scale from old to new rect (FLIP on x, y, width, height with split-axes stiffness), staggered 15–25 ms by index.
- Access: segmented control with `aria-pressed`; motion only, content order unchanged.

### Context menu from the pointer
- Sentence: the menu grows out of the exact point you clicked, width first, and shrinks back into it when dismissed.
- Origin at the pointer; split axes from 0×0 (width k 320, height k 160); items stagger 30 ms; hover highlight is a vertical edge pair.
- Access: `role=menu`, arrow keys, Esc, return focus to the invoking element.

### Date picker (now built: catalog #23)
- Sentence: the selected-day highlight worms between days, and changing months slides the grid with a jelly skew.
- Day highlight: 2-D, so use two edge pairs (x and y) or, across rows, collapse to a dot, move, and expand. Month change: track spring with velocity skew as in the carousel. Range selection: per-row capsules, each an edge pair.
- Access: grid with `role=grid`, arrow keys move the focused day, Page Up/Down change months.

## Porting to React (pattern)

Keep springs and DOM writes outside React's render cycle; keep the *state* in React.

```jsx
import { useEffect, useLayoutEffect, useRef } from 'react';
import { edgePair } from './stretchy-core';   // export what you need from the core

export function WormTabs({ tabs, value, onChange }) {
  const indRef = useRef(null), btnRefs = useRef([]), ep = useRef(null), first = useRef(true);

  if (!ep.current) ep.current = edgePair((L, R) => {
    const el = indRef.current; if (!el) return;            // unmounted mid-animation
    el.style.transform = `translateX(${L}px)`;
    el.style.width = `${Math.max(0, R - L)}px`;
  });

  const place = (animate) => {
    const b = btnRefs.current[value]; if (!b) return;
    const a = b.offsetLeft, z = a + b.offsetWidth;
    animate ? ep.current.to(a, z) : ep.current.set(a, z);
  };

  useLayoutEffect(() => { place(!first.current); first.current = false; }, [value]);

  useEffect(() => {                                        // re-measure on resize and font load
    const ro = new ResizeObserver(() => place(false));
    ro.observe(indRef.current.parentElement);
    document.fonts?.ready.then(() => place(false));
    return () => ro.disconnect();
  }, [value]);

  return (
    <div className="seg" role="tablist">
      <span className="seg-ind" ref={indRef} />
      {tabs.map((t, i) => (
        <button key={t} role="tab" ref={el => (btnRefs.current[i] = el)}
          aria-selected={i === value} tabIndex={i === value ? 0 : -1}
          className={i === value ? 'on' : ''} onClick={() => onChange(i)}>{t}</button>
      ))}
    </div>
  );
}
```

The same shape works in Vue (`ref`, `onMounted`, `watch`) and Svelte (`bind:this`, `$:`). Never put spring values in component state; a re-render per frame drops frames and fights the spring.
