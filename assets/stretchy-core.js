/* =====================================================================
   stretchy-core.js  —  spring engine + stretch helpers, no dependencies.
   Paste inline into a page (globals), or turn into a module by adding
   `export` in front of the declarations you need.
   ===================================================================== */

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const lerp = (a, b, t) => a + (b - a) * t;
const RM = matchMedia('(prefers-reduced-motion: reduce)');

/* Global damping multiplier. 1.8 = soft, 1 = bouncy, 0.5 = very stretchy.
   Read on every tick, so changing it retunes animations already running. */
let bounce = 1;
function setBounce(x) { bounce = x; }

/* ---------------------------------------------------------------------
   Spring: damped oscillator, semi-implicit Euler, 8 substeps per frame.
   new Spring(x0, {k, c, eps, onUpdate(x, v), onRest()})
     .to(t, {k, c})  retarget, keeps velocity (interruptible)
     .set(x)         jump, no animation
     .drag(x, v)     follow a pointer, recording velocity
     .kick(v)        add an impulse (wobble feedback)
   x is in whatever unit you like (px, 0..1, degrees). Pick eps to match:
   0.05 for px springs that only draw, ~0.5 for px springs whose onRest
   triggers logic, 0.001 for 0..1 springs.
   --------------------------------------------------------------------- */
class Spring {
  constructor(x, o = {}) {
    this.x = x; this.v = 0; this.t = x;
    this.k = o.k ?? 220; this.c = o.c ?? 18; this.eps = o.eps ?? 0.05;
    this.cb = o.onUpdate || (() => {}); this.rest = o.onRest || null;
    this.raf = 0; this.tick = this.tick.bind(this);
  }
  to(t, o) {
    if (o) { if (o.k) this.k = o.k; if (o.c) this.c = o.c; }
    this.t = t;
    if (RM.matches) {             // reduced motion: snap, but still fire onRest
      cancelAnimationFrame(this.raf); this.raf = 0;
      this.x = t; this.v = 0; this.cb(t, 0); this.rest && this.rest(); return this;
    }
    if (!this.raf) { this.last = performance.now(); this.raf = requestAnimationFrame(this.tick); }
    return this;
  }
  set(x) { cancelAnimationFrame(this.raf); this.raf = 0; this.x = this.t = x; this.v = 0; this.cb(x, 0); }
  drag(x, v) { cancelAnimationFrame(this.raf); this.raf = 0; this.x = this.t = x; this.v = v; this.cb(x, v); }
  kick(v) { if (RM.matches) return; this.v += v; this.to(this.t); }
  tick(now) {
    const dt = Math.max(0, Math.min((now - this.last) / 1000, 1 / 30)); this.last = now;
    const n = 8, h = dt / n, c = this.c * bounce;
    for (let i = 0; i < n; i++) {
      const a = -this.k * (this.x - this.t) - c * this.v;
      this.v += a * h; this.x += this.v * h;
    }
    if (Math.abs(this.v) < this.eps && Math.abs(this.x - this.t) < this.eps) {
      this.x = this.t; this.v = 0; this.raf = 0; this.cb(this.x, 0); this.rest && this.rest(); return;
    }
    this.cb(this.x, this.v);
    this.raf = requestAnimationFrame(this.tick);
  }
}

/* ---------------------------------------------------------------------
   edgePair: two springs for the two edges of something that travels
   between slots. The edge facing the direction of travel is stiff, the
   other soft, so the shape stretches on the way and contracts on arrival.
   draw(L, R) receives both edges (left/right or top/bottom).
   --------------------------------------------------------------------- */
function edgePair(draw, o = {}) {
  const fast = o.fast || { k: 420, c: 30 }, slow = o.slow || { k: 150, c: 18 };
  let L = 0, R = 0;
  const l = new Spring(0, { onUpdate: x => { L = x; draw(L, R); } });
  const r = new Spring(0, { onUpdate: x => { R = x; draw(L, R); } });
  return {
    set(a, b) { l.set(a); r.set(b); },
    to(a, b) {
      if (a >= l.t) { r.to(b, fast); l.to(a, slow); }   // moving right/down: R leads
      else { l.to(a, fast); r.to(b, slow); }            // moving left/up: L leads
    }
  };
}

/* ---------------------------------------------------------------------
   Resync registry: re-measure after fonts load and on resize.
   --------------------------------------------------------------------- */
const resyncs = [];
const onResync = f => resyncs.push(f);
const resyncAll = () => resyncs.forEach(f => f());
addEventListener('resize', resyncAll);
if (document.fonts) document.fonts.ready.then(resyncAll);

/* ---------------------------------------------------------------------
   makeSegmented: segmented control / tab bar with a worm indicator.
   Markup: <div class="seg"><span class="seg-ind"></span><button data-seg>…</button>…</div>
   The root must be position:relative; the indicator absolute, left:0.
   --------------------------------------------------------------------- */
function makeSegmented(root, { attr = 'aria-pressed', initial = 0, onChange } = {}) {
  const btns = $$('[data-seg]', root), ind = $('.seg-ind', root); let cur = -1;
  const ep = edgePair((L, R) => { ind.style.transform = `translateX(${L}px)`; ind.style.width = Math.max(0, R - L) + 'px'; });
  const pos = i => [btns[i].offsetLeft, btns[i].offsetLeft + btns[i].offsetWidth];
  function select(i, anim = true, notify = true) {
    if (i === cur) return; cur = i;
    btns.forEach((b, j) => {
      b.setAttribute(attr, String(j === i)); b.classList.toggle('on', j === i);
      if (attr === 'aria-selected') b.tabIndex = j === i ? 0 : -1;
    });
    const [a, b] = pos(i); anim ? ep.to(a, b) : ep.set(a, b);
    if (notify && onChange) onChange(i, btns[i]);
  }
  btns.forEach((b, i) => b.addEventListener('click', () => select(i)));
  root.addEventListener('keydown', e => {
    const d = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0; if (!d) return;
    e.preventDefault(); const n = (cur + d + btns.length) % btns.length; select(n); btns[n].focus();
  });
  select(initial, false, false);
  onResync(() => { const [a, b] = pos(cur); ep.set(a, b); });
  return { select, get index() { return cur; } };
}

/* ---------------------------------------------------------------------
   Deformation helpers
   --------------------------------------------------------------------- */

/* Volume preservation: when width changes with velocity v (px/s), return a
   scale for the other axis. Keep lo/hi tight (≈0.93..1.07) for controls. */
const volumeScale = (v, k = 9000, lo = 0.93, hi = 1.07) => clamp(1 - v / k, lo, hi);

/* Stretch along a direction of travel. Returns a transform fragment that
   lengthens along (vx, vy) and thins across it while keeping content upright. */
function alongVelocity(vx, vy, { max = 0.35, div = 3400, thin = 0.45 } = {}) {
  const sp = Math.hypot(vx, vy); if (sp < 40) return '';
  const a = Math.atan2(vy, vx) * 180 / Math.PI, s = Math.min(max, sp / div);
  return `rotate(${a}deg) scale(${1 + s},${1 - s * thin}) rotate(${-a}deg)`;
}

/* Bulging edges for big moving surfaces (draw the surface as an SVG path).
   b = edgeBulge(v): the middle lags behind the direction of motion. */
const edgeBulge = (v, k = 0.05, max = 56) => clamp(-v * k, -max, max);
/* Surface anchored left, moving right edge (sidebar). */
const rightEdgePath = (w, h, b) => `M0 0H${w}Q${w + b} ${h / 2} ${w} ${h}H0Z`;
/* Surface anchored bottom, moving top edge with rounded corners (sheet).
   `extra` extends below so an upward overshoot never shows a gap. */
const topEdgePath = (w, h, r, b, extra = 60) =>
  `M0 ${r}Q0 0 ${r} 0Q${w / 2} ${b} ${w - r} 0Q${w} 0 ${w} ${r}V${h + extra}H0Z`;

/* ---------------------------------------------------------------------
   flipReorder: animate a list reorder with springs that keep velocity,
   stretching items vertically while they move.
   els: the items; mutate(): reorders the DOM.
   --------------------------------------------------------------------- */
function flipReorder(els, mutate) {
  const first = new Map(els.map(e => [e, e.getBoundingClientRect().top]));
  mutate();
  els.forEach(e => {
    if (!e._flip) e._flip = new Spring(0, { k: 230, c: 20, onUpdate: (y, v) => {
      e.style.transform = `translateY(${y}px) scale(${1 - Math.min(.05, Math.abs(v) / 14000)},${1 + Math.min(.14, Math.abs(v) / 5000)})`;
    } });
    const d = first.get(e) - e.getBoundingClientRect().top;
    e._flip.drag(e._flip.x + d, e._flip.v); e._flip.to(0);
  });
}

/* ---------------------------------------------------------------------
   throwTo: lift a clone of `fromEl` off the page, shrink it into a round
   chip and throw it along an arc into `toEl` (add-to-cart, save-to-folder,
   send-to-inbox…). Time-based so the arc is predictable; stretch comes from
   the frame-to-frame velocity. `container` must be position:relative and
   contain both elements.
   --------------------------------------------------------------------- */
function throwTo({ container, fromEl, toEl, background = 'transparent', duration = 800,
                   arc = 90, endSize = 30, startRadius = 20, pad = 20, onArrive = () => {} }) {
  if (RM.matches) { onArrive(); return; }
  const easeIO = t => t < .5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
  const easeOut = t => 1 - Math.pow(1 - t, 3);
  const sr = container.getBoundingClientRect(), a = fromEl.getBoundingClientRect(), c = toEl.getBoundingClientRect();
  const x0 = a.left + a.width / 2 - sr.left, y0 = a.top + a.height / 2 - sr.top;
  const x1 = c.left + c.width / 2 - sr.left, y1 = c.top + c.height / 2 - sr.top;
  const w0 = a.width + pad, h0 = a.height + pad;
  const cx = x0 + (x1 - x0) * .35, cy = Math.min(y0, y1) - arc, t0 = performance.now();
  const el = document.createElement('div');
  Object.assign(el.style, {
    position: 'absolute', left: 0, top: 0, zIndex: 5, display: 'grid', placeItems: 'center',
    overflow: 'hidden', pointerEvents: 'none', background, borderRadius: startRadius + 'px',
    boxShadow: '0 16px 30px -12px rgba(20,10,60,.5)', transition: 'opacity .16s'
  });
  const clone = fromEl.cloneNode(true); clone.removeAttribute('style'); clone.removeAttribute('id');
  Object.assign(clone.style, { width: '84%', height: '84%' });
  el.appendChild(clone); container.appendChild(el);
  let px = x0, py = y0, pt = t0, st = 0, ang = 0;
  (function frame(now) {
    const t = clamp((now - t0) / duration, 0, 1);
    const lift = Math.sin(clamp(t / .14, 0, 1) * Math.PI / 2) * (1 - clamp((t - .14) / .3, 0, 1));
    const u = easeIO(clamp((t - .1) / .9, 0, 1)), s = easeOut(clamp((t - .08) / .72, 0, 1));
    const bx = (1 - u) * (1 - u) * x0 + 2 * u * (1 - u) * cx + u * u * x1;
    const by = (1 - u) * (1 - u) * y0 + 2 * u * (1 - u) * cy + u * u * y1 - lift * 12;
    const dt = Math.max(1, now - pt), vx = (bx - px) / dt * 1000, vy = (by - py) / dt * 1000;
    px = bx; py = by; pt = now;
    const sp = Math.hypot(vx, vy);
    st = st * .7 + Math.min(.34, sp / 3400) * .3; if (sp > 40) ang = Math.atan2(vy, vx) * 180 / Math.PI;
    const sc = 1 + lift * .08;
    el.style.width = lerp(w0, endSize, s) + 'px'; el.style.height = lerp(h0, endSize, s) + 'px';
    el.style.borderRadius = lerp(startRadius, endSize / 2, s) + 'px';
    el.style.transform = `translate(${bx}px,${by}px) translate(-50%,-50%) rotate(${ang}deg) scale(${(1 + st) * sc},${(1 - st * .45) * sc}) rotate(${-ang}deg)`;
    if (t < 1) requestAnimationFrame(frame);
    else { el.style.opacity = 0; el.style.transform += ' scale(.4)'; setTimeout(() => el.remove(), 180); onArrive(); }
  })(t0);
}

/* Restart a CSS keyframe animation (e.g. a ring pulse on arrival). */
function replayClass(el, cls) { el.classList.remove(cls); void el.offsetWidth; el.classList.add(cls); }
