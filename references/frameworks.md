# Using the core in React, Vue, Svelte and server-rendered pages

Read this when the target is a framework codebase or an existing site rather than a new standalone page.

## Get the core in

- Check for an existing copy first: `grep -rl "class Spring" src` (use the project's source folder). If the stretchy core is already there, import that copy; never add a second one.
- Framework with a bundler: `python scripts/add_core.py --module src/lib/stretchy-core.js` (pick the project's own lib folder) writes the core as an ES module with every top-level name exported. Import what you need: `import { Spring, edgePair, makeSegmented } from './lib/stretchy-core'`. Never re-type the core.
- Importing it is safe during server rendering (Next.js, Nuxt, SvelteKit, Astro): loading it touches no DOM. Constructing a `Spring` or an `edgePair` touches no DOM and may happen during render (as in the port below); measure, call `set()` / `to()`, and call `makeSegmented` / `makeAccordion` only in mount hooks (`useEffect` / `useLayoutEffect`, `onMounted`, `onMount`).
- Server-rendered or CMS templates with no bundler: copy `assets/stretchy-core.js` next to the site's scripts, load it with one `<script>` tag before your own script, and attach behaviour to markup through data attributes.
- TypeScript: the module is plain JS; add `// @ts-nocheck` at its top or a small `.d.ts` only if the project's type check complains.

## Rules

- Keep the *state* (selected tab, count, open or closed) in the framework; springs animate presentation only.
- Create springs once (`useRef`, `onMounted`, module scope of a Svelte component), write styles to element refs inside `onUpdate`. Never put spring values in component state: a re-render per frame drops frames and fights the spring.
- Update `aria-*` and focus through the framework's state on the same event that starts the animation.
- Tear down on unmount: `spring.stop()`, `edgePair.stop()`, `destroy()` on `makeSegmented` / `makeAccordion`, and call the function `onResync(f)` returned.
- Measure in layout effects and re-measure on resize and font load (`ResizeObserver`, `document.fonts.ready`).
- Keep the component's public API unchanged; change the smallest surface that achieves the effect.

## Component libraries and existing animation

A library that renders the markup (Radix, Headless UI, MUI): add the indicator as an extra element positioned from measured trigger rects, do not fork the library; its items paint their own background and switch the selected style at once, so move the surface under the indicator and delay the selected look until the indicator arrives (SKILL.md, "Moving indicators"). An animation library already on the element (Framer Motion, React Spring, GSAP): reuse its springs with the same technique or replace it on that component only; never run two systems on one element. `<details>` / accordions rendered by a framework: see `python scripts/show_component.py accordion --recipe` (render `.acc-panel > .acc-in` yourself, leave `open` unbound, `makeAccordion` on mount, `destroy()` on unmount).

## React port (pattern)

Keep springs and DOM writes outside React's render cycle; keep the *state* in React.

```jsx
import { useEffect, useLayoutEffect, useRef } from 'react';
import { edgePair } from './lib/stretchy-core';   // written by: python scripts/add_core.py --module src/lib/stretchy-core.js

export function WormTabs({ tabs, value, onChange }) {
  const indRef = useRef(null), btnRefs = useRef([]), ep = useRef(null), first = useRef(true);
  const cur = useRef(value), tgt = useRef([0, 0]), lit = useRef(-1);

  // The selected look (.on) is a class the animation sets, never a React prop: it arrives
  // with the indicator, not with the click (SKILL.md, "Moving indicators", rule 1).
  const light = (i) => { lit.current = i; btnRefs.current.forEach((b, j) => b && b.classList.toggle('on', j === i)); };

  if (!ep.current) ep.current = edgePair((L, R) => {
    const el = indRef.current; if (!el) return;            // unmounted mid-animation
    el.style.transform = `translateX(${L}px)`;
    el.style.width = `${Math.max(0, R - L)}px`;
    if (lit.current !== cur.current && L <= tgt.current[0] + 2 && R >= tgt.current[1] - 2) light(cur.current);
  });

  const place = (animate) => {
    const b = btnRefs.current[value]; if (!b) return;
    const a = b.offsetLeft, z = a + b.offsetWidth;
    cur.current = value; tgt.current = [a, z];
    if (animate) { light(-1); ep.current.to(a, z); } else ep.current.set(a, z);
  };
  const placeRef = useRef(place); placeRef.current = place;   // latest closure for the observers below

  useLayoutEffect(() => { place(!first.current); first.current = false; }, [value]);

  useEffect(() => {                                        // re-measure on resize and font load
    const ro = new ResizeObserver(() => placeRef.current(false));
    ro.observe(indRef.current.parentElement);
    document.fonts?.ready.then(() => placeRef.current(false));
    return () => ro.disconnect();
  }, []);                                                  // once: re-running it on every click would snap the worm

  useEffect(() => () => ep.current.stop(), []);            // stop the springs on unmount

  return (
    <div className="seg" role="tablist" onKeyDown={e => {
      const d = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0; if (!d) return;
      e.preventDefault(); const n = (value + d + tabs.length) % tabs.length;
      onChange(n); btnRefs.current[n]?.focus();
    }}>
      <span className="seg-ind" ref={indRef} />
      {tabs.map((t, i) => (
        <button key={t} role="tab" ref={el => (btnRefs.current[i] = el)}
          aria-selected={i === value} tabIndex={i === value ? 0 : -1}
          onClick={() => onChange(i)}>{t}</button>
      ))}
    </div>
  );
}
```

> Layering (rule 2) is CSS: `.seg{position:relative;isolation:isolate}`, `.seg-ind{position:absolute;left:0;z-index:-1;pointer-events:none}`, each button's surface and border in a `::before` at `z-index:-2`, the button itself with no background, and the selected look on the class the animation sets (`.seg button.on{color:#fff}`).

The same shape works in Vue (`ref`, `onMounted`, `watch`) and Svelte (`bind:this`, `$:`). Never put spring values in component state; a re-render per frame drops frames and fights the spring.

### When a library renders the tabs (Radix, Headless UI, MUI)

Keep the library's components: focus handling and `aria-*` stay theirs. Put `<span className="seg-ind" ref={indRef} />` inside the list (`Tabs.List`), give the list a ref, and collect the triggers with `listRef.current.querySelectorAll('[role="tab"]')` in place of `btnRefs`. Drive the same `edgePair` from the controlled `value`. The library flips `data-state="active"` (or `aria-selected`) at click: do not style the selected look on that attribute. Style the `.on` class that the draw callback sets, and override the trigger's own background to transparent so the indicator is not hidden behind it.

## Check it

Run the project's own type check, lint and tests. Start the project's dev server (`npm run dev` or the stack's equivalent), then `python scripts/check_page.py http://localhost:PORT/route --frames "CLICK_SELECTOR@CLIP_SELECTOR"` and look at the frames and jump strips.
