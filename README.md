# stretchy-morph-ui

สกิลสำหรับ Claude ที่ทำให้ UI บนเว็บ **morph แบบยืดหยุ่นเหมือนยาง**: องค์ประกอบจะบีบ ยืด เด้งเลยเป้าแล้วค่อยนิ่ง โดยใช้ spring แทน easing curve

ตัวอย่างเช่น เส้นใต้แท็บที่ยืดตัวแบบหนอนไปหาแท็บถัดไป ปุ่มที่หดเป็นวงโหลดแล้วพองกลับ หรือรูปสินค้าที่ลอยออกจากการ์ด หดเป็นวงกลม แล้วตกลงในตะกร้า

> **หลักการเดียวของสกิลนี้:** การยืดต้องมีสาเหตุ
> ขอบหน้าไปถึงก่อนขอบหลัง, เคลื่อนที่เร็วเลยยืดตามทิศทาง, ถูกบีบเลยพองอีกแกนเพื่อรักษาปริมาตร, หรือถูกกระทบเลยสั่น
> ถ้าดุ๊กดิ๊กวนไปเรื่อย ๆ โดยไม่มีสาเหตุจะดูถูก ๆ แต่ถ้ายืดเพราะมีสาเหตุจะดูเหมือนวัสดุจริง

## สิ่งที่อยู่ในสกิล

- **Spring engine** ไม่มี dependency (`assets/stretchy-core.js`) พร้อมฟังก์ชันช่วย เช่น edge pair, volume preservation, bulging SVG edge, FLIP reorder, thrown object
- **Showcase 22 คอมโพเนนต์** ที่ใช้งานได้จริง ได้แก่ tabs, stepper, sidebar, carousel, send button, toggles, radio/checkbox, chips, search, dropdown, slider, quantity, rating, add to cart, goo menu, modal, toast, tooltip, bottom sheet, FAB, accordion และ dynamic island
- **เทคนิคการยืด 11+ แบบ** พร้อมโค้ดและค่า spring ที่ปรับไว้แล้ว
- **วิธีออกแบบคอมโพเนนต์ใหม่** ที่ไม่อยู่ในแคตตาล็อก พร้อมตัวอย่าง 14 แบบ (pull to refresh, swipe to delete, OTP input, date picker ฯลฯ) และแนวทาง port ไป React
- **สคริปต์ตรวจหน้าเว็บ** ด้วย headless Chromium ตรวจ JS error, การล้นจอแนวนอน, layer ล่องหนที่บังการคลิก และถ่ายภาพเฟรมแอนิเมชันมาเรียงเป็น contact sheet

## โครงสร้าง

```
stretchy-morph-ui/
├── SKILL.md                    คำสั่งหลักที่ Claude อ่าน (workflow, กฎ, checklist)
├── references/
│   ├── techniques.md           เทคนิคการยืดแต่ละแบบ โค้ด และค่าที่ใช้ปรับ
│   ├── components.md           แคตตาล็อกคอมโพเนนต์: recipe, ค่า spring, ข้อควรระวัง
│   └── new-components.md       วิธีออกแบบคอมโพเนนต์ใหม่ + ตัวอย่าง + React port
├── assets/
│   ├── stretchy-core.js        spring engine + helpers
│   ├── starter.html            โครงหน้าเปล่า (light/dark, ฟอนต์ไทย, reduced motion)
│   └── showcase.html           คอมโพเนนต์ทั้ง 22 ตัว
└── scripts/
    └── check_page.py           smoke test + ถ่ายเฟรมแอนิเมชัน
```

## ติดตั้ง

### Claude Code

clone repo นี้ไปไว้ในโฟลเดอร์ skills

```bash
# ใช้ได้ทุกโปรเจกต์
git clone <repo-url> ~/.claude/skills/stretchy-morph-ui

# หรือเฉพาะโปรเจกต์เดียว
git clone <repo-url> .claude/skills/stretchy-morph-ui
```

### claude.ai

zip โฟลเดอร์นี้ (ให้ `stretchy-morph-ui/` อยู่ชั้นบนสุดใน zip) แล้วอัปโหลดในหน้า Settings → Capabilities → Skills

```bash
zip -r stretchy-morph-ui.skill stretchy-morph-ui -x "*.git*"
```

## การใช้งาน

ไม่ต้องเรียกสกิลเอง Claude จะหยิบไปใช้เมื่อคำขอเกี่ยวกับ UI ที่เคลื่อนไหว เช่น

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
