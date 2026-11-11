# stretchy-morph-ui

สกิลสำหรับ AI coding agent (Claude และ Google Antigravity) ที่ทำให้ UI บนเว็บ **morph แบบยืดหยุ่นเหมือนยาง**: องค์ประกอบจะบีบ ยืด เด้งเลยเป้าแล้วค่อยนิ่ง โดยใช้ spring แทน easing curve

ตัวอย่างเช่น เส้นใต้แท็บที่ยืดตัวแบบหนอนไปหาแท็บถัดไป ปุ่มที่หดเป็นวงโหลดแล้วพองกลับ หรือรูปสินค้าที่ลอยออกจากการ์ด หดเป็นวงกลม แล้วตกลงในตะกร้า

> **หลักการเดียวของสกิลนี้:** การยืดต้องมีสาเหตุ
> ขอบหน้าไปถึงก่อนขอบหลัง, เคลื่อนที่เร็วเลยยืดตามทิศทาง, ถูกบีบเลยพองอีกแกนเพื่อรักษาปริมาตร, หรือถูกกระทบเลยสั่น
> ถ้าดุ๊กดิ๊กวนไปเรื่อย ๆ โดยไม่มีสาเหตุจะดูถูก ๆ แต่ถ้ายืดเพราะมีสาเหตุจะดูเหมือนวัสดุจริง

## สิ่งที่อยู่ในสกิล

- **Spring engine** ไม่มี dependency (`assets/stretchy-core.js`) พร้อมฟังก์ชันช่วย เช่น edge pair, volume preservation, bulging SVG edge, FLIP reorder, thrown object
- **Showcase 23 คอมโพเนนต์** ที่ใช้งานได้จริง ได้แก่ tabs, stepper, sidebar, carousel, send button, toggles, radio/checkbox, chips, search, dropdown, slider, quantity, rating, add to cart, goo menu, modal, toast, tooltip, bottom sheet, FAB, accordion, dynamic island และ date picker (เลือกวันเดียวหรือช่วง)
- **เทคนิคการยืด 11+ แบบ** พร้อมโค้ดและค่า spring ที่ปรับไว้แล้ว
- **วิธีออกแบบคอมโพเนนต์ใหม่** ที่ไม่อยู่ในแคตตาล็อก พร้อมตัวอย่าง 14 แบบ (pull to refresh, swipe to delete, OTP input, date picker ฯลฯ) และแนวทาง port ไป React
- **ขั้นตอน audit โค้ดของผู้ใช้ก่อนลงมือ** (Step 0) สแกนโค้ดที่มีอยู่ด้วย `scripts/audit_ui.py` หาส่วนที่ทำให้ยืดได้ (tabs, toggle, modal, dropdown, accordion ฯลฯ) สรุปเป็นรายการพร้อม `file:line` แล้วถามผู้ใช้ให้ยืนยันหรือเพิ่มเอง **ก่อนแก้ไฟล์ใด ๆ**
- **สคริปต์ตรวจหน้าเว็บ** ด้วย headless Chromium ตรวจ JS error, การล้นจอแนวนอน, layer ล่องหนที่บังการคลิก และถ่ายภาพเฟรมแอนิเมชันมาเรียงเป็น contact sheet

## โครงสร้าง

```
stretchy-morph-ui/
├── SKILL.md                    คำสั่งหลักที่ Claude อ่าน (workflow, กฎ, checklist)
├── references/
│   ├── audit.md                วิธีหา สแกน ตัดสิน และจัดลำดับส่วนที่ควรทำให้ยืด + แม่แบบข้อความถามยืนยัน (ไทย/อังกฤษ)
│   ├── techniques.md           เทคนิคการยืดแต่ละแบบ โค้ด และค่าที่ใช้ปรับ
│   ├── components.md           แคตตาล็อกคอมโพเนนต์: recipe, ค่า spring, ข้อควรระวัง
│   └── new-components.md       วิธีออกแบบคอมโพเนนต์ใหม่ + ตัวอย่าง + React port
├── assets/
│   ├── stretchy-core.js        spring engine + helpers
│   ├── starter.html            โครงหน้าเปล่า (light/dark, ฟอนต์ไทย, reduced motion)
│   └── showcase.html           คอมโพเนนต์ทั้ง 23 ตัว
└── scripts/
    ├── audit_ui.py             สแกนโค้ดของผู้ใช้: stack, แอนิเมชันที่มีอยู่, ส่วนที่ทำให้ยืดได้
    └── check_page.py           smoke test + ถ่ายเฟรมแอนิเมชัน
```

## ติดตั้ง

สกิลนี้ใช้รูปแบบมาตรฐาน `SKILL.md` (frontmatter มี `name` + `description`) จึงใช้โฟลเดอร์เดียวกันได้ทั้ง Claude และ Antigravity ไม่ต้องแปลงไฟล์ แค่ clone ไปวางในตำแหน่งที่แต่ละเครื่องมือค้นหาสกิล

| เครื่องมือ | ทุกโปรเจกต์ (global) | เฉพาะโปรเจกต์ (workspace) |
|---|---|---|
| Claude Code | `~/.claude/skills/stretchy-morph-ui/` | `.claude/skills/stretchy-morph-ui/` |
| Antigravity (IDE และ `agy` CLI) | `~/.gemini/config/skills/stretchy-morph-ui/` | `.agents/skills/stretchy-morph-ui/` |

### Claude Code

```bash
# ทุกโปรเจกต์
git clone <repo-url> ~/.claude/skills/stretchy-morph-ui

# เฉพาะโปรเจกต์
git clone <repo-url> .claude/skills/stretchy-morph-ui
```

### Antigravity

```bash
# ทุกโปรเจกต์
git clone <repo-url> ~/.gemini/config/skills/stretchy-morph-ui

# เฉพาะโปรเจกต์ (commit .agents/ ขึ้น git เพื่อแชร์ให้ทีมได้)
git clone <repo-url> .agents/skills/stretchy-morph-ui
```

Antigravity ยังรับ `.agent/`, `_agents/`, `_agent/` แทน `.agents/` ได้ด้วย และจะค้นจากโฟลเดอร์ที่เปิดอยู่ขึ้นไปจนถึง root ของ repo

ถ้าอยากเก็บ repo ไว้ที่อื่น ให้ลงทะเบียนโฟลเดอร์แม่ของสกิลใน `skills.json` (วางใน `~/.gemini/config/` หรือ `.agents/` ของโปรเจกต์) Antigravity จะสแกนโฟลเดอร์ใน `path` ลงไปหนึ่งชั้น

```json
{
  "entries": [
    { "path": "~/src/my-skills", "include_only": ["stretchy-morph-ui"] }
  ]
}
```

### ใช้ร่วมกันทั้งสองเครื่องมือ (Windows)

clone ไว้ที่เดียว แล้วสร้าง junction ชี้ไปจากอีกที่ แก้ไฟล์ครั้งเดียวจะเห็นผลทั้งคู่ (junction บน Windows ไม่ต้องใช้สิทธิ์ admin)

```powershell
git clone <repo-url> "$HOME\.claude\skills\stretchy-morph-ui"
New-Item -ItemType Junction -Path "$HOME\.gemini\config\skills\stretchy-morph-ui" `
         -Target "$HOME\.claude\skills\stretchy-morph-ui"
```

บน macOS / Linux ใช้ `ln -s ~/.claude/skills/stretchy-morph-ui ~/.gemini/config/skills/stretchy-morph-ui`

### claude.ai

zip โฟลเดอร์นี้ (ให้ `stretchy-morph-ui/` อยู่ชั้นบนสุดใน zip) แล้วอัปโหลดในหน้า Settings → Capabilities → Skills

```bash
zip -r stretchy-morph-ui.skill stretchy-morph-ui -x "*.git*"
```

## การใช้งาน

ไม่ต้องเรียกสกิลเอง agent (Claude หรือ Antigravity) จะหยิบไปใช้เมื่อคำขอเกี่ยวกับ UI ที่เคลื่อนไหว เช่น

- "ทำ tab ที่เส้นใต้ยืดตอนเปลี่ยนแท็บ"
- "ทำปุ่ม add to cart ให้รูปบินเข้าตะกร้า"
- "ทำให้หน้านี้ดูมีชีวิต เด้ง ๆ หน่อย"
- "make this toggle feel more springy / gooey / elastic"

### ใช้ spring engine ตรง ๆ

`stretchy-core.js` ใช้แยกจากสกิลได้ แค่วางไว้ใน `<script>` (เป็น global) หรือใส่ `export` หน้าสิ่งที่ต้องการเพื่อทำเป็น module

```js
const box = document.querySelector('.box');

const w = new Spring(120, {
  k: 280, c: 20,                       // stiffness, damping
  onUpdate: x => box.style.width = x + 'px',
});

w.to(320);      // ไปที่เป้าหมาย โดยเก็บความเร็วเดิมไว้ (กดรัว ๆ ก็ต่อเนื่อง)
w.kick(8);      // กระตุกให้สั่นแล้วนิ่ง
setBounce(0.5); // ปรับความเด้งทั้งหน้า: 1.8 นุ่ม, 1 เด้ง, 0.5 ยืดมาก
```

ถ้าผู้ใช้เปิด `prefers-reduced-motion: reduce` อยู่ `to()` จะกระโดดไปเป้าหมายทันทีและเรียก `onRest` เลย โค้ดที่รอแอนิเมชันจบจึงยังทำงานต่อได้

### สแกนโค้ดว่าตรงไหนทำให้ยืดได้

ไม่ต้องติดตั้งอะไรเพิ่ม (Python ล้วน) รับได้ทั้งไฟล์และโฟลเดอร์ รองรับ HTML/CSS/JS และเฟรมเวิร์กทั่วไป

```bash
python scripts/audit_ui.py ./src
python scripts/audit_ui.py ./src --json --max-hits 10
```

ผลลัพธ์บอก stack ที่พบ, แอนิเมชันและ `prefers-reduced-motion` ที่มีอยู่แล้ว, และรายการแยกตามประเภท พร้อมบอกว่าแต่ละอันจะกลายเป็นอะไรและใช้เทคนิคไหน ผลนี้เป็นแค่การคัดกรองด้วย heuristic ต้องอ่านโค้ดรอบ ๆ ทุกจุดก่อนเสนอผู้ใช้

### ตรวจหน้าเว็บ

ต้องมี Playwright

```bash
pip install playwright
playwright install chromium

# ตรวจ error, การล้นจอ, ตัวบังการคลิก ที่ความกว้าง 1280 และ 390
python scripts/check_page.py assets/showcase.html --out out/

# คลิก selector แล้วถ่าย 8 เฟรม ห่างกัน 110 ms ครอปเฉพาะ .stage
python scripts/check_page.py page.html --frames "#tabs button:nth-child(3)@.stage"
```

exit code เป็น 1 เมื่อพบปัญหา จึงใช้ใน CI ได้

## ค่า spring ที่ใช้บ่อย

| บทบาท | k | c |
|---|---|---|
| ขอบนำของ edge pair | 420–520 | 30–34 |
| ขอบตามของ edge pair | 140–170 | 17–19 |
| ความกว้างของ container | 240–320 | 18–24 |
| ความสูงของ container | 150–170 | 15–17 |
| kick feedback | 380–420 | 12–16 |

Damping ratio ζ = c / (2√k): การเปลี่ยน state ทั่วไปอยู่ราว 0.6–0.8, feedback แบบขี้เล่นราว 0.3–0.5, เกิน 1 จะไม่เด้งเลยเป้า

รายละเอียดเพิ่มเติมอยู่ใน [`SKILL.md`](SKILL.md) และ [`references/techniques.md`](references/techniques.md)
