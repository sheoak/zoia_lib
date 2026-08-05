---
name: zoia-patch-edit
description: Edit Empress ZOIA .bin patches as JSON using AI. Use when the user asks to inspect, modify, or generate a ZOIA patch — e.g. "add a delay", "make this brighter", "retune this patch", "what modules are in this patch", or any request involving a .bin ZOIA patch file.
---

# Editing ZOIA patches with AI

ZOIA patches are binary `.bin` files. This skill lets you edit them as plain
JSON: **decode** a `.bin` to JSON, edit the JSON, then **encode** it back.

## Workflow

All commands run from the repo root (`/Users/sheoak/Dev/zoia_lib`):

```bash
# 1. Binary -> editable JSON
python -m zoia_lib.backend.patch_cli decode  patch.bin  patch.json

# 2. Quick human summary of a patch (no file written)
python -m zoia_lib.backend.patch_cli info    patch.bin

# 3. Edit patch.json with the Edit/Write tools (see structure below)

# 4. Edited JSON -> binary
python -m zoia_lib.backend.patch_cli encode  patch.json out.bin

# 5. Study how faithfully a patch survives decode->encode
python -m zoia_lib.backend.patch_cli roundtrip patch.bin
```

The JSON is exactly the dict produced by the parser, so `encode` reads back
anything `decode` wrote. Prefer editing the JSON with targeted `Edit` calls
over regenerating it wholesale.

## Fidelity — where the encoder stands

The encoder is **byte-exact on real patches**. Verified with `roundtrip`:
The Hierophant, The Star and The Magician all come back with 0 differing bytes.
Measured over a 216-patch collection, 186 (86%) are byte-exact, and no patch
re-encodes differently while decoding to an identical dict — the
silent-corruption class is empty.

Still worth doing:

- **Run `roundtrip` on the source `.bin` first.** If it is not byte-exact
  before your edit, it will not be after.
- After encoding, re-decode to confirm the result parses:
  `python -m zoia_lib.backend.patch_cli info out.bin`.
- Structural changes (adding or removing modules and connections) remain the
  riskiest, because the raw fields described below cannot be carried over for
  something that did not exist in the source file.

Known non-byte-exact case: `zoia_lib/tests/sample_files/input_test.bin`, a
synthetic fixture (46 differing bytes). It re-decodes cleanly; the old
color-id `KeyError` is gone.

## ⚠️ Raw fields win — edit these, not the friendly ones

Most values are decoded twice: a friendly form for humans and the raw bytes
read from the file. **The encoder prefers the raw form**, so editing only the
friendly field silently does nothing:

```
d["modules"][0]["parameters"]["value"] = 0.10   # ignored, file unchanged
d["modules"][0]["parameters_raw"][0]   = 6553   # this is what gets written
```

| Friendly field | Raw field the encoder uses instead |
| --- | --- |
| `module.parameters` (0.0-1.0) | `parameters_raw` — list of ints, 0-65535 |
| `module.page` | `page_raw` |
| `module.options` / `options_binary` | `options_raw` — list of 8 bytes |
| `module.color` | `header_color_id` **and** the trailing `colors` list |
| `connection.source` / `destination` / `strength` | `source_raw`, `source_block_raw`, `dest_raw`, `dest_block_raw`, `strength_raw` |
| `pages` / `pages_count` | `pages_raw` / `pages_count_raw` |
| `starred[].block` | `block_raw` |

**Always set the raw field. Do not delete it to fall back on the friendly one**
— the friendly forms are lossy display values:

- `parameters` is `round(raw / 65535, 2)`. Raw 15500 reads as 0.24 and
  re-encodes as 15728, so dropping `parameters_raw` drifts *every* parameter of
  that module.
- `strength` is `int(strength_raw / 100)`, truncated. Raw counts hundredths of a
  percent, the device range is 0-999%, and raw values are often not multiples of
  100 (6990 shows as 69) — deriving raw from `strength` rewrites them.
- Colour is stored twice and the two can genuinely disagree. The trailing
  `colors` list wins when `len(colors) == len(modules)`, so set both it and
  `header_color_id`.

**Verification trick:** after an edit, `roundtrip` reporting 0 differing bytes
means the edit was **ignored**. A real edit always changes bytes.

This precedence is deliberate: it is what makes patches rebuildable. The
module index does not describe every option a module can carry, Euroburo I/O
modules sit on page 127 (outside the 0-63 grid), and page names exist for pages
holding no module — all of which the friendly form cannot represent.

## Names — 16 bytes, and keep them under 16

Name fields (patch name, module names, page names) are fixed 16-**byte**
fields, NUL-padded. Any UTF-8 is fine, apostrophes and accents included:
`Café`, `L'Hierophante`, `naïve résumé` all round-trip intact.

Two limits to respect:

- The budget is **bytes, not characters**. An accented character costs 2, so
  `Don't Panic Café` (16 characters, 17 bytes) is truncated to
  `Don't Panic Caf`.
- **Keep the patch name at 15 bytes or fewer.** A name filling all 16 leaves
  no NUL terminator, and `parse_data` decodes the patch name with an unbounded
  slice (`self._qc_name(byt[4:])`), so it runs into the next field:
  `ABCDEFGHIJKLMNOP` decodes as `ABCDEFGHIJKLMNOP�` and re-encodes
  corrupted. Module names are unaffected — their call site bounds the slice to
  16 bytes.

## JSON structure

Top-level keys: `name`, `size`, `modules`, `connections`, `pages`,
`pages_count`, `pages_raw`, `pages_count_raw`, `starred`, `colors`, `meta`.

A **module** looks like:

```json
{
  "number": 0,             // index of this module in the list
  "mod_idx": 1,            // module TYPE id -> see ModuleIndex.json
  "type": "Audio Input",   // resolved from mod_idx
  "name": "my osc",        // user-assigned label, 16 bytes max
  "category": "Interface",
  "cpu": 0.3,
  "page": 0,               // grid page, 0-63 (127 for Euroburo I/O)
  "page_raw": 0,           // what the encoder actually writes
  "position": [0, 1],      // grid block indices the module occupies
  "color": "Blue",         // header color (see palette below)
  "header_color_id": 1,    // what the encoder actually writes
  "options": {"channels": "stereo"},
  "options_binary": {...},
  "options_raw": [1, 0, 0, 0, 0, 0, 0, 0],   // 8 bytes, wins over the above
  "parameters": {"level": 0.5},              // name -> normalized 0.0-1.0
  "parameters_raw": [32767],                 // ints 0-65535, wins over the above
  "blocks": {...}, "params": 1, "version": 0, "size": 12,
  "saved_data": [...], "size_of_saveable_data": 0,
  "connections": [...],
  "starred": [...]
}
```

A **connection**: `{"source": "0.1", "destination": "0.0", "strength": 0}`
where `"module.block"` addresses a block. The raw counterparts (`source_raw`,
`source_block_raw`, `dest_raw`, `dest_block_raw`, `strength_raw`) are what the
encoder writes. `strength_raw` counts hundredths of a percent and can exceed
10000: the device range is 0-999%, so a connection applies
`source × (strength_raw / 10000)` and values above 100% amplify the CV.

`pages` is a list of page-name strings, `pages_raw` the untrimmed list read
from the file. `meta` is a computed summary (regenerated on decode; you don't
need to hand-edit it).

A **star** on a connection rather than a module parameter stores a negative
`module` index and `-1` in `block_raw`. Leave those entries alone.

## Module reference

The authoritative module database is
`zoia_lib/common/schemas/ModuleIndex.json`, keyed by `mod_idx` (as a string).
Read it to learn a module's real parameter names, value ranges/units
(`param_defaults`), block layout, options, and CPU. Do this before changing
parameters so you use correct names and 0.0-1.0 normalized values.

## Color palette

Header colors (name used in JSON): Blue, Green, Red, Yellow, Aqua, Magenta,
White, Orange, Lima, Surf, Sky, Purple, Pink, Peach, Mango.

## Tips for musical edits

- "Brighter": raise filter cutoff / high-frequency params toward 1.0 — via
  `parameters_raw` (0-65535), or delete it and set `parameters`.
- "Add a module": copy an existing module dict, give it a fresh `number`, a
  free `position` on some `page`, then (optionally) wire it with a connection.
  Drop the copied `parameters_raw` / `options_raw` / `saved_data` unless the new
  module is the same type as the one you copied — stale raw bytes are worse than
  none.
- Always confirm the intended musical result with `info` and, when possible, by
  re-decoding the encoded `.bin`.
- Mirror the wiring conventions already in the patch rather than inventing new
  ones; minimal edits survive best.
