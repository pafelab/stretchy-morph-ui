# Audit the user's code, then confirm

Every time this skill is used, start here. The user wants to know *what in their own interface* can become stretchy before anything is changed. This file covers finding the code, scanning it, judging the candidates, and asking for confirmation.

Contents
1. Find the code
2. Scan
3. Judge each candidate
4. Prioritise
5. Present and confirm (templates)
6. After the reply

---

## 1. Find the code

Look in this order and use everything that exists:

- Code pasted into the conversation.
- Files the user attached (on claude.ai they are under `/mnt/user-data/uploads`; list the folder, since a message may say "attached" when nothing came through, or files may be there that were never mentioned).
- The working directory or repository (Claude Code, Cowork, or a cloned repo): the project root, `src/`, `app/`, `components/`, `pages/`, `templates/`.
- A claude.ai artifact link: read it with the artifact tool so its files land in the container.
- A connected source (GitHub, Drive) if the user points to one.

If there is no code anywhere, do not guess and do not silently build a demo. Say what you looked for, then offer the two ways forward: share the code (attach, paste, a path or a link), or build something new from scratch (then skip to the normal workflow in SKILL.md, still confirming the list of components first).

If the codebase is large, ask nothing yet: scan everything, then focus the reading on the screens with the most candidates and on shared components (a `Button` or `Tabs` used in 40 places is worth more than a one-off page).

## 2. Scan

```bash
python scripts/audit_ui.py <paths…>            # readable report
python scripts/audit_ui.py <paths…> --json     # if you want to post-process
```

The report gives the stack (framework, Tailwind, component libraries, animation libraries), how much motion exists today, whether `prefers-reduced-motion` is handled, and candidates per UI category with `file:line` and a snippet, each mapped to a showcase component and technique.

For pasted code with no files, either save it to a temp file and scan it, or read it directly against the category list in `audit_ui.py`.

The scanner is a keyword pass. It finds dead CSS, commented-out code and words used in other senses ("cart" in a URL, "modal" in a class nobody uses). Every candidate must be confirmed by reading the code around the hit.

## 3. Judge each candidate

For each real candidate, write down:

- **Where:** file and line (or component name), and how many places use it.
- **Now:** what happens today in one short phrase ("underline jumps instantly", "panel appears with no transition", "button text changes to กำลังเพิ่ม…").
- **Becomes:** the morph sentence ("the indicator stretches like a worm to the new tab because its leading edge is stiffer").
- **Effort:** small (one component, no structural change), medium (new markup layer, measuring, or touching a shared component), large (new interaction such as drag, cross-component choreography like the cart throw, or replacing a library's internals).
- **Risk or dependency:** anything that can bite, for example:
  - A component library renders the markup (Radix, Headless UI, MUI): the indicator usually has to be an extra element positioned from measured trigger rects, without forking the library.
  - An animation library is already in use (Framer Motion, React Spring, GSAP): either reuse its springs with the same technique, or replace it on that component only; do not run two systems on one element.
  - A native control (`<select>`, `<input type="date">`): replacing it costs accessibility and mobile pickers. Prefer animating around it, or propose a custom control only where the user benefits, and say so.
  - Server-rendered or CMS templates: the core must be loaded as a separate script and attach to markup by data attributes.
  - Lists with hundreds of rows: do not give every row its own running spring.

Skip, and say why, when a candidate would hurt: dense data tables, forms where speed matters more than delight, admin screens used all day, or anything already animated well.

## 4. Prioritise

Rank by visibility × frequency × fit:

1. **High:** seen on every visit or at a key moment (primary nav tabs, add to cart, submit buttons, the main toggle), and a direct catalog match.
2. **Medium:** visible but secondary (FAQ accordion, filter chips, toasts, dropdowns).
3. **Optional:** rare or expensive (date picker replacement, drag to reorder, page transitions).

Group duplicates: twelve buttons with loading states are one proposal ("all submit buttons via the shared `Button`"), not twelve.

Also list cross-cutting work that comes with any change: adding the core once (as a module or script), reduced-motion handling if the scan found none, and a global bounce setting if they want one.

Cap the list at about ten items so the choice stays easy; mention that more exist if they do.

## 5. Present and confirm

Write in the user's language. Lead with what you looked at, then the proposals, then the question. Do not edit anything yet.

Thai template:

```
ตรวจโค้ดแล้ว: 6 ไฟล์ (React + Tailwind, ใช้ react-hot-toast, ยังไม่รองรับการลดการเคลื่อนไหว)

แนะนำมาก
1. แท็บสินค้า (ProductTabs.tsx:5) ตอนนี้เส้นใต้กระโดดทันที → ตัวชี้ยืดแบบหนอนไปหาแท็บใหม่ [เล็ก]
2. ปุ่มเพิ่มลงตะกร้า (ProductCard.tsx:15) ตอนนี้แค่เปลี่ยนข้อความ → รูปสินค้าลอยเข้าตะกร้า ปุ่มหดเป็นวงพร้อมเครื่องหมายถูกแล้วกลายเป็นตัวนับจำนวน [ใหญ่]

น่าทำ
3. คำถามที่พบบ่อย (Faq.tsx:2, <details>) → ความสูงพุ่งเลยแล้วดีดกลับ [เล็ก]
…

ไม่แนะนำ
- ช่องเลือกวันที่ (Checkout.tsx:10) เป็นช่องวันที่ของเบราว์เซอร์ ถ้าเปลี่ยนเป็นปฏิทินเองจะเสียตัวเลือกวันที่ของมือถือ บอกได้ถ้ายังอยากเปลี่ยน

เลือกได้เลยว่าจะให้ทำข้อไหน (เช่น "1, 2, 5" หรือ "ทั้งหมดที่แนะนำ") และถ้ามีส่วนอื่นที่อยากให้ยืดได้แต่ไม่อยู่ในรายการ พิมพ์เพิ่มมาได้
```

English template: the same structure with "Recommended", "Worth doing", "Not recommended", and the closing question "Tell me which to do (for example "1, 2, 5" or "all recommended"), and add anything else you want to feel stretchy that isn't listed."

If the environment has a tappable-choice tool (for example `ask_user_input_v0` on claude.ai), send the full list as text first, then offer the choice through the tool so it is one tap on mobile. The tool takes 2–4 options per question, so offer groups rather than every item:

- multi-select "จะให้ทำส่วนไหน": "ทั้งหมดที่แนะนำ (1–2)", "แนะนำ + น่าทำ (1–6)", "เลือกเองตามหมายเลข", "มีส่วนอื่นจะเพิ่ม"
- optionally single-select "ความเด้ง": "นุ่ม", "เด้ง", "ยืดสุด"

Remind them they can also type numbers or extra requests. If no such tool exists (Claude Code, API), ask in plain text. Either way, end the turn after asking.

If the user's request already named specific parts ("make my tabs stretchy"), still run the audit, put their parts first marked as requested, list the other candidates as optional, and ask a shorter question: "จะทำแท็บตามที่ขอ จะเพิ่มข้อไหนจากรายการด้วยไหม".

## 6. After the reply

- Build only what was chosen, plus anything they added in their own words (treat additions like new candidates: read the code, pick the technique, mention effort if it is large).
- If a choice is ambiguous ("ทำปุ่ม" with three kinds of buttons listed), make the reasonable pick and say which in one line rather than asking again.
- Follow the workflow in SKILL.md: add the core once, keep the component's public API unchanged, keep state in the framework and springs out of it, handle reduced motion, focus and `aria-*`.
- Change the smallest surface that achieves the effect: wrap or extend existing components instead of rewriting screens.
- Verify: run the project's own checks if there are any (type check, lint, tests), and for anything that renders as a standalone page, `scripts/check_page.py` with frame contact sheets of each converted interaction. Look at the frames.
- Report per item: what changed, which files, anything left undone or deferred, and how to tune it (which spring values or the global bounce).
