# Audit the user's code, then confirm

Read this only at Step 0: the request is about the user's existing interface in general and names no specific parts. This file covers finding the code (or live page), scanning it, judging the candidates, and asking for confirmation. Make no edits before the user replies.

Contents
1. Find the code or live page
2. Scan
3. Judge each candidate
4. Prioritise
5. Present and confirm (templates)
6. After the reply

---

## 1. Find the code or live page

Look in this order and use everything that exists:

- Code pasted into the conversation (pipe directly to `audit_ui.py --stdin --ext .tsx` or `.html`).
- Files the user attached (on claude.ai they are under `/mnt/user-data/uploads`; list the folder, since a message may say "attached" when nothing came through, or files may be there that were never mentioned).
- The working directory or repository (Claude Code, Cowork, or a cloned repo): the project root, `src/`, `app/`, `components/`, `pages/`, `views/`, `templates/`, `resources/views/`.
- A running dev server or live website URL (`http://localhost:PORT/...` or `https://...`), e.g. WordPress, Shopify, Webflow, compiled SPAs, or Tailwind-only apps where static class names are opaque.
- A claude.ai artifact link: read it with the artifact tool so its files land in the container.
- A connected source (GitHub, Drive) if the user points to one.

If there is no code or URL anywhere, do not guess and do not silently build a demo. Say what you looked for, then offer the two ways forward: share the code or URL (attach, paste, a path or a link), or build something new from scratch (then go to the Workflow in SKILL.md).

If the codebase is large, ask nothing yet: scan everything, then focus the reading on the screens with the most candidates and on shared components (a `Button` or `Tabs` used in 40 places is worth more than a one-off page).

## 2. Scan

```bash
python scripts/audit_ui.py <paths…>                 # static scan of local files/folders
python scripts/audit_ui.py http://localhost:5173/   # live DOM + computed-style scan of a URL
python scripts/audit_ui.py page.html --dom          # static scan + live DOM scan of local HTML
python scripts/audit_ui.py --stdin --ext .tsx       # scan pasted code directly from stdin
python scripts/audit_ui.py <paths…> --json          # compact JSON for post-processing
```

What the scanner covers:
- **Static codebases (zero dependencies):** HTML/CSS/SCSS/Less/Stylus, JS/TS/JSX/TSX/MDX, Vue, Svelte, Astro, Angular, Web Components (`.webc`), and server/CMS templates (PHP/Blade, ERB, Twig, Handlebars, Nunjucks, Liquid, EJS, Pug, Jinja2/Django, Razor/Blazor, JSP, Phoenix HEEx, Go Templ). Recognises Tailwind/utility-first hooks (`activeTab`, `isModalOpen`, `viewMode`, etc.), `data-bs-*` / Flowbite / DaisyUI / Alpine.js / HTMX / UIkit attributes, framework component prefixes (`v-*`, `el-*`, `n-*`, `q-*`, `p-*`, `mat-*`, `sl-*`, `ion-*`, `x-*`), native `<dialog>` / `popover`, and Thai UI labels.
- **Live DOM (`http(s)://` URLs or `--dom`):** Runs in headless Chromium (Playwright, falling back to Selenium+Chromium, or static HTTP HTML fetch if neither is installed). Traverses open **Shadow DOM** and runs computed-style / structural heuristics (horizontal button/link rows with an active background or underline, `aria-expanded` disclosures, horizontal scroll-snap card tracks, fixed sidebars/bottom sheets/FABs), so it still detects UI on Tailwind-only, CSS-in-JS, Webflow, WordPress, Shopify, and obfuscated-class sites. Useful flags: `--wait-ms 1500` (hydration wait), `--viewport 1280x900`, `--channel chromium|msedge|chrome`.

The report gives the stack (framework, styling, component/animation libraries, CMS/Web Components, or an existing copy of the stretchy core), how much motion exists today, whether `prefers-reduced-motion` is handled, shared components with their use counts (PascalCase and custom kebab-case tags), and candidates per UI category: `file:line` (`d` = definition line) for static hits, or `[DOM]: selector` for live-DOM hits, mapped to a showcase component and technique. Tests, stories, minified and generated files, comment lines and the skill's own folder are skipped, as is a copy of the stretchy core already in the project; CSS-only matches are flagged "CSS only". `--max-hits N` (default 6) sets how many hits each category shows.

A local path that does not exist stops the scan with one line and exit code 2.

The scanner is a heuristic pass: it still finds words used in other senses ("cart" in a variable name, a "modal" class nobody uses) or structural false positives in live DOM. Confirm every candidate by reading the code around the hit (definition line first, then one usage) or checking the matched DOM selector.

## 3. Judge each candidate

For each real candidate, write down:

- **Where:** file and line (or component name, or DOM selector for a live URL), and how many places use it.
- **Now:** what happens today in one short phrase ("underline jumps instantly", "panel appears with no transition", "button text changes to กำลังเพิ่ม…").
- **Becomes:** the morph sentence ("the indicator stretches like a worm to the new tab because its leading edge is stiffer").
- **Effort:** small (one component, no structural change), medium (new markup layer, measuring, or touching a shared component), large (new interaction such as drag, cross-component choreography like the cart throw, or replacing a library's internals).
- **Risk or dependency:** anything that can bite, for example:
  - A component library renders the markup (Radix, Headless UI, MUI, Vuetify, Element Plus, Prime, Shoelace): the indicator usually has to be an extra element positioned from measured trigger rects, without forking the library. Its items usually paint their own background and switch their selected style the moment the state changes; plan to move the surface under the indicator and delay the selected look until the indicator arrives (SKILL.md, "Moving indicators").
  - Web Components / Shadow DOM (Shoelace, Lit, Ionic): outer CSS cannot pierce closed shadow roots; either style exposed `::part(...)` / CSS custom properties or wrap/replace the specific control.
  - An animation library is already in use (Framer Motion, React Spring, GSAP, AutoAnimate): either reuse its springs with the same technique, or replace it on that component only; do not run two systems on one element. A widget library that animates itself (react-hot-toast, Sonner, a carousel package) counts the same way: replace it on that widget only, or leave it and say so.
  - A native control (`<select>`, `<input type="date">`): replacing it costs accessibility and mobile pickers. Prefer animating around it, or propose a custom control only where the user benefits, and say so.
  - Server-rendered, CMS, or no-code sites (WordPress, Shopify, Webflow, Laravel Blade, Django, Bootstrap/Alpine/HTMX): load the core as a separate script and attach to markup by data attributes or selectors; re-bind after HTMX swaps (`htmx:afterSwap`).
  - `<details>`/`<summary>` in plain, server-rendered or CMS HTML: low risk. `makeAccordion(container)` enhances them in place, keeps them working without JS and with find-in-page, and turns a `name` group into a one-open-at-a-time accordion. Effort is usually small.
  - `<details>` or accordions rendered by React, Vue or Svelte: do **not** run `makeAccordion` on raw framework markup: it re-parents each item's children and writes `open`, which the framework does not know about (a later update can throw, a bound `open` fights it). Render `.acc-panel > .acc-in` yourself, leave `open` unbound, call the helper once on mount and its `destroy()` on unmount, or port the recipe as a component (React example: `references/frameworks.md`). Details: `python scripts/show_component.py accordion --recipe`. Effort: medium.
  - Lists with hundreds of rows: do not give every row its own running spring.
  - The stretchy core is already in the codebase (the scan says so): reuse that copy; never add a second one.

Skip, and say why, when a candidate would hurt: dense data tables, forms where speed matters more than delight, admin screens used all day, or anything already animated well.

## 4. Prioritise

Rank by visibility × frequency × fit:

1. **High:** seen on every visit or at a key moment (primary nav tabs, add to cart, submit buttons, the main toggle), and a direct catalog match.
2. **Medium:** visible but secondary (FAQ accordion, filter chips, toasts, dropdowns, notification bell, theme toggle).
3. **Optional:** rare or expensive (date picker replacement, drag to reorder, page transitions, command palette).

Group duplicates: twelve buttons with loading states are one proposal ("all submit buttons via the shared `Button`"), not twelve.

Also list cross-cutting work that comes with any change: adding the core once (see `references/frameworks.md` for a framework codebase), reduced-motion handling if the scan found none, and a global bounce setting if they want one.

Cap the list at about ten items so the choice stays easy; mention that more exist if they do.

## 5. Present and confirm

Write in the user's language. Lead with what you looked at, then the proposals, then the question. Do not edit anything yet.

Thai template:

```
ตรวจโค้ดแล้ว: 6 ไฟล์ (React + Tailwind, ยังไม่รองรับการลดการเคลื่อนไหว)

แนะนำมาก
1. แท็บสินค้า (ProductTabs.tsx:5) ตอนนี้เส้นใต้กระโดดทันที → ตัวชี้ยืดแบบหนอนไปหาแท็บใหม่ [เล็ก]

น่าทำ
2. คำถามที่พบบ่อย (Faq.tsx:2, <details>) → ความสูงพุ่งเลยแล้วดีดกลับ [กลาง]

ไม่แนะนำ
- ช่องเลือกวันที่ (Checkout.tsx:10) เป็นช่องวันที่ของเบราว์เซอร์ ถ้าเปลี่ยนเป็นปฏิทินเองจะเสียตัวเลือกวันที่ของมือถือ

เลือกได้เลยว่าจะให้ทำข้อไหน (เช่น "1, 2" หรือ "ทั้งหมดที่แนะนำ") และถ้ามีส่วนอื่นที่อยากให้ยืดได้แต่ไม่อยู่ในรายการ พิมพ์เพิ่มมาได้
```

Each item: where (file:line or DOM selector), what happens now → what it becomes, [effort: เล็ก / กลาง / ใหญ่ or small / medium / large].

English template: the same structure with "Recommended", "Worth doing", "Not recommended", and the closing question "Tell me which to do (for example "1, 2" or "all recommended"), and add anything else you want to feel stretchy that isn't listed."

If the environment has a tappable-choice tool (`ask_user_input_v0` on claude.ai, `AskUserQuestion` in Claude Code), send the full list as text first, then offer the choice through the tool so it is one tap on mobile. The tool takes 2–4 options per question, so offer groups rather than every item:

- multi-select "จะให้ทำส่วนไหน": "ทั้งหมดที่แนะนำ (1–n)", "แนะนำ + น่าทำ (1–m)", "เลือกเองตามหมายเลข", "มีส่วนอื่นจะเพิ่ม"
- optionally single-select "ความเด้ง": "นุ่ม", "เด้ง", "ยืดสุด"

Remind them they can also type numbers or extra requests. If no such tool exists (for example over the API), ask in plain text. Either way, end the turn after asking.

## 6. After the reply

- Build only what was chosen, plus anything they added in their own words (treat additions like new candidates: read the code, pick the technique, mention effort if it is large).
- If a choice is ambiguous ("ทำปุ่ม" with three kinds of buttons listed), make the reasonable pick and say which in one line rather than asking again.
- Follow the workflow in SKILL.md: add the core once (framework codebase: `python scripts/add_core.py --module <dest.js>`, and read `references/frameworks.md`), keep the component's public API unchanged, keep state in the framework and springs out of it, handle reduced motion, focus and `aria-*`.
- Change the smallest surface that achieves the effect: wrap or extend existing components instead of rewriting screens.
- Verify: run the project's own checks if there are any (type check, lint, tests). Then `python scripts/check_page.py <file.html or http://localhost:PORT/route>` with `--frames` for each converted interaction: it checks a standalone page or the running dev server. Look at the frames.
- Report per item: what changed, which files, anything left undone or deferred, and how to tune it (which spring values or the global bounce).
