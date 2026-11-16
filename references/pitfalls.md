# Pitfalls and polish lessons

Read this when a page misbehaves or looks cheap, before porting a catalog component into an existing codebase, and before you judge captured frames. Both parts come from real bugs and design corrections in the 24-component build.

## Symptom, cause, fix

| Symptom | Cause | Fix |
|---|---|---|
| Wide block children shrink-wrapped and centred | `place-items:center` on a `display:block` container now aligns block children in Chromium | Give block stages `place-items:normal` |
| Whole page scrolls sideways on phones | `grid-template-columns:1fr` lets a child's min-content (a carousel track) blow out the column | Use `minmax(0,1fr)` |
| Button could not be clicked | An invisible (opacity 0) sibling layer sat on top of it | `pointer-events:none` on hidden layers |
| Indicator lands in the wrong place on first paint | Measured before the web font loaded | Re-measure on `document.fonts.ready` and resize |
| The clicked chip vanished for ~0.2 s on every pick (ported choice chips) | The selected style (white label, transparent fill) was bound to the selected state, so it switched on at click while the capsule was still travelling: white on white | Switch the visual style when the indicator covers the item (SKILL.md, "Moving indicators", rule 1) |
| The capsule showed only in the gaps between chips, as broken pieces | Each chip kept its own `background`, painted above the capsule | Surfaces in `::before` at `z-index:-2`, capsule at `-1`, container `isolation:isolate` (SKILL.md, "Moving indicators", rule 2) |
| The capsule showed a white ring over every chip it crossed | The chip borders were on the chips themselves, so they painted above the capsule | Draw the border on the surface `::before` too; the chip keeps only a transparent border (SKILL.md, "Moving indicators", rule 2) |
| Dialog lingered ~1 s after visibly closing | Rest threshold `eps` of 0.05 px is far stricter than the eye | Use `eps≈0.5` for pixel springs whose `onRest` triggers logic |
| Under reduced motion, a measured size was stale (choice chips) | `*{transition-duration:.01s!important}` keeps `transition-property:all`, so a size a spring writes becomes a 10 ms transition and an immediate measurement reads the old layout | `transition:none!important` on elements whose size a spring writes and another part measures |
| Slider broke after adding the date picker | Both declared `function setVal`; in one script the later declaration silently replaces the earlier | Prefix helpers per component (`dpText`), or wrap each component in its own block or module; check with `grep -oE "function [A-Za-z_]+" \| sort \| uniq -d` |
| A helper worked in the skill's starter but threw in a bigger page | The page never included it (`replayClass`) | Paste the whole core, or inline the two lines you need |

## Making it look good

The first add-to-cart version flew a plain coloured ball along two independent springs, shrank the button into an empty violet oval and squashed the cart. The user said it was not pretty. What fixed it generalises:

- **Move the real thing.** Clone the product picture, lift it slightly with a shadow, then shrink it into a round chip that still shows the picture while it flies. Abstract dots read as debug output.
- **Intermediate shapes must carry meaning.** A shrunken button is an empty blob unless it shows something: a spinner, a check that draws itself, a count. The add button now becomes a green circle with a check, then grows into the − n + stepper.
- **Subtle volume on controls.** A ±18 % vertical bulge on a button looked like a pill-shaped egg. ±7 % reads as soft material.
- **Arrival needs a receiver.** The cart icon dips and tilts, a ring pulses out, the badge pops. Something must visibly *catch* what was thrown.
- **Don't clip status marks.** A badge inside a morphing `overflow:hidden` pill gets cut off; put it in a wrapper outside the clip.
- **Don't repeat information.** The cart pill showed "3 ชิ้น 195 บาท" next to a badge saying 3. It now shows only the total.
- **Draw illustrations at a fixed aspect.** Percent-positioned CSS shapes inside a tile stretch when the tile widens. Use an inline SVG with a viewBox, centred in the tile.
