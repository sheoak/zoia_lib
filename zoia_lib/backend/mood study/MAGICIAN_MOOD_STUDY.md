# The Magician (I) — Mood/Blooper study & build notes

Goal patch: **The Magician (arcana I)** — a Chase-Bliss-Mood / Blooper-flavoured engine:
*capture what you play, then transmute it* (scan/stretch/freeze/reverse/pitch/degrade)
and let it echo/haunt in reverb. "Master who transmutes raw matter." Arcana chosen by
the user (over Death / Wheel of Fortune).

Built by studying 4 patches in `zoia_lib/backend/mood study/`:
`061_zoia_my_mood`, `004_zoia_moodz`, `061_zoia_Moody_Bloopy`, `010_zoia_Mude_v1`
(`008_PhantomAppendge` won't parse — compact layout, skip).

---

## ⚠️ ZOIA Looper module (idx30) — the peculiar record/play control

Blocks: `audio_in`, `record`, `restart_playback`, `stop_play`, `speed_pitch`,
`reverse_playback`, `audio_out`. **With option `length_edit: on` it ALSO exposes
`start_position` + `loop_length`.**

Behaviour (from web + patches; VERIFY on device — Christopher's explanation not yet
found, search again e.g. "Christopher H ZOIA looper" / Empress forum):
- **record**: press → records; the **first pass sets the loop length**; then it
  auto-loops. Can be a **momentary** button (hold-to-record) OR **latching** (toggle) —
  both patterns are used. `overdub: yes` → sound-on-sound layering (Blooper-style).
- **stop_play**: play/pause toggle. Often a **latching** button set `normally: one`
  so the loop defaults to playing.
- **restart_playback**: retrigger from the start.
- **speed_pitch**: playback speed = pitch (double/half). Reverse via negative / the
  reverse block. Octave up/down done with a Pushbutton + **CV Invert** pair.
- **reverse_playback**: reverse the loop.

**Options seen:** `max_rec_time` (4/8/16/32s), **`length_edit`** (on = Mood head/length),
`playback` (loop/once), **`length`** (fixed / **pre_speed**), `hear_while_rec`,
`play_reverse`, **`overdub`** (yes = layering), `stop_play_button`.

### Observed control wiring (concrete, working)
- **my_mood**: `record` ← Pushbutton *momentary* (hold-to-record); `stop_play` ←
  Pushbutton *latching, normally one*; `reverse` ← Pushbutton *latching*.
- **moodz**: `record` ← Stompswitch *latching*; `length_edit=on` so `start_position`,
  `loop_length`, `reverse` are driven by **MIDI CC In** (ch4, CC15/16/17). Also a
  Pitch Shifter fed by the looper with `pitch_shift` ← "loop stretch" knob.
- **Moody_Bloopy**: "Moody" = momentary record + latching stop + pitch-up Pushbutton +
  CV Invert; "Bloopy" = latching record, **`overdub: yes`** (32s), `length: pre_speed`.

**Takeaway:** the Looper CAN do Mood-style **head (`start_position`) + length
(`loop_length`)** — just set `length_edit: on`. I was wrong earlier saying it can't.

---

## Granular module (idx83) — the other Mood core (head/length/freeze/speed)

Blocks: `audio_in_L/R`, `grain_size`, `grain_position`, `density`, `texture`,
`speed_pitch`, `freeze`, `audio_out_L/R`.
**Options (REQUIRED): `pos_control: cv`, `size_control: cv`** so position/size are
knob/CV-controllable; `num_grains` (1–8), `channels`, `max_grain_size` (≤ 1s).
- `grain_position` = **head** · `grain_size` = **length** · `speed_pitch` = speed
  (negative = reverse) · `freeze` = hold/capture the buffer.
- Decouples head & length (what a plain Delay Line can't). ~17 CPU, **short buffer**
  (≤1s) — good for haunted fragments, not long loops.

## Delay Line (idx13) as a continuous circular buffer
Always records the last N sec. `delay_time` = head distance **AND** loop length
(coupled — one control). `feedback` = **sustain/decay, NOT length** (don't conflate —
mistake made once). Freeze = feedback→1.0 (infinite sustain), length stays = delay_time.

---

## Transformation / "modifiers" palette (Blooper stability / Magician transmutation)
Pitch Shifter (idx59, stretch/octave) · Reverse Delay (idx106, unnatural suck) ·
SV Filter (idx0) / Multi Filter (idx24) · Aliaser (bit-crush/degrade) · Random (idx39,
re-roll per cycle) · Delay w/Mod (idx43, `old_tape`) · speed/reverse on Looper/Granular.
moodz chains: **Looper → Pitch Shifter (stretch) + Granular (grain scan)** through
filter/aliaser. Moody_Bloopy: **two loopers** (Mood no-overdub + Bloopy overdub) + tape
delay + granular texture.

---

## MOOD MkII — accurate manual reference (user-supplied, from the official manual)

**Micro-Looper channel** — always-listening (records continuously when bypassed; turn on
to hear what it caught). Loop length set by **CLOCK** (not manual). Two knobs LENGTH +
MODIFY, whose job changes per mode:
- **ENV** (audio-controlled): interrupts the loop with your playing → dynamic stutters /
  frozen notes. Chops loop into slices; **while sound is detected at input it repeats the
  current slice** until sound disappears. LENGTH = slice size (low=micro grains, high=short
  phrases). MODIFY = **audio-detector sensitivity** (lower=less sensitive). Trick: crank
  sensitivity + play very quietly → loop slows to a crawl (time-stretch by touch).
- **TAPE** (tape-style): adjust **speed & direction in harmonized OCTAVE steps** (REV 4x/2x/
  1x/0.5x … FWD 0.5x/1x/2x/4x), + shorten loop. LENGTH = shrink loop (CCW=shorter).
  MODIFY = speed/direction.
- **STRETCH** (time-stretch): chops loop into slices and **moves through them at a chosen
  SPEED**. LENGTH = slice size (high=clear/repeating, low=blurry/grainy; classic stretch is
  CCW of noon). MODIFY = **direction + amount of stretch** (nearer noon = slower progress;
  MODIFY at MAX = NO effect).

**Wet/Spatial channel** (OBNE) — 3 modes: **REVERB · DELAY · SLIP**.
- **SLIP** (auto-sampler + pitch-shifter): samples input continuously, replays at a chosen
  speed/direction → harmonies + pitch-shift. **TIME = sample size** (low=instant pitch-shift;
  high=harmonized phrases that trail behind = pitch-shifted delay). **MODIFY = playback
  speed/direction in SEMITONE steps** (neutral centre). → ZOIA: short Delay(TIME) → Pitch
  Shifter idx59 (pitch_shift=MODIFY). Pitch Shifter has ONLY pitch_shift (no window).

**Overdubbing:** hold footswitch to overdub. **Only the CLEAN INPUT is overdubbed** — the
Wet effects are heard but NOT recorded into the micro-loop (avoids feedback), UNLESS the
looper is bypassed/always-listening (then wet IS captured). Loop-mode playback tricks
(shorten/stretch/slow/interrupt) can misplace where overdubs land. (My build records AIN =
clean input → faithful.)

**SPREAD (dip):** turns each mode into a stereo-IMAGE effect (Mood is stereo by default;
SPREAD *changes* the image, doesn't enable stereo). OFF = preserves input image. ON =
alters/exaggerates it. Per mode: REVERB=pans each tap (scatter); DELAY=ping-pong L/R;
SLIP=smooth pan (speed=TIME+CLOCK); ENV=holds image until input>threshold then pans L/R
(speed=LENGTH+CLOCK); TAPE=right ch plays loop forward, left ch plays it reversed;
STRETCH=slow smooth side-to-side pan (speed=MODIFY+CLOCK).

**CLOCK (the master knob):** sets MOOD's **sample rate** = tone + length + quality in one.
Wet: quality & time of effects. Loop: length & resolution. Lower = aliasing/downsampling
(lo-fi/computer noise, ambient/gritty); higher = pure/hi-fi. Moves in **musical harmonized
steps** (e.g. 64k→32k = half-speeds both loop and wet, i.e. −1 octave). **SMOOTH CLOCK**
(MkII dip) = fluid CLOCK sweep. → ZOIA has no sample-rate control; approximate CLOCK as a
macro tying loop-length + delay-time + pitch (+ an Aliaser/bit-crush for the lo-fi).

**RAMPING waveform (hidden option):** shape of auto-ramp modulation — Triangle, Square,
Sine, Random, Smooth Random (warp between). → ZOIA: an LFO (idx5) with selectable shape
driving the auto-sweeps (Stretch scan, SPREAD panning, etc.).

## ROADMAP (user-set versioning)
- **V1** (current target): faithful-minimal Mood clone. **No overdub, buffer ≤1s**
  (Granular native), **one FIXED simple wet effect** (ambient, Mood-ish — delay→reverb
  TBD), **stomps LEFT + RIGHT only**, **3-mode routing switch** on page 0.
  - Stomp LEFT = Loop channel: tap engage (freeze buffer + hear loop) / bypass (release,
    keeps recording, dry passes). Freeze tied to the left stomp (only 2 stomps in V1).
  - Stomp RIGHT = Wet channel: tap engage/bypass.
  - **Routing** = what feeds the Wet channel (accurate Mood 3-way): **IN / BOTH / LOOP**
    (input only / input+loop / loop only). Page-0 **UI Button that cycles** the 3 modes.
  - Loop = Granular (always-listening, `pos_control:cv`, `size_control:cv`): knobs Tête
    (`grain_position`) / Longueur (`grain_size`) / Vitesse (`speed_pitch`, neg=reverse).
- **V1.2**: **totally custom effects** in the wet/modifier chain — the user's own effect
  set (not the Mood's), beyond the single fixed V1 effect.
- **V2**: **extended buffer >1s** (combine Delay Line feeding the Granular, or a Looper,
  for longer capture than the 1s Granular limit). NB: likely an engine change (Looper).
- **V3**: **overdub** (sound-on-sound layering — Looper `overdub:yes` / feedback layering).
- **V4**: **tempo/clock sync** (loop length/timing quantised to tempo, sit in-time —
  addresses the Mood's "hard to get in-time" gripe).

**Improvement ideas over the Mood (from common-complaints research)** — slot into the
versions above: repeatability/recall (precise knob values, patch saves state, quantisable
head/length), clean page-0 UI (vs Mood's cryptic DIPs), a proper lush reverb (The Star,
not a texture-verb), tempo sync (V4). The Mood's real weak point is repeatability — worth
prioritising.

## DECISION: patch is **STEREO IN → STEREO OUT** (user)
So both L+R carry the stereo audio → **no spare channel for an external FX loop**. The
mono FX-loop-on-R idea below is therefore **shelved**; V1's wet channel is **internal**
(reverb/delay, stereo). Everything stereo end-to-end.

## V1 wet approach — external FX LOOP idea (SHELVED — incompatible with stereo I/O)
Instead of a fixed internal wet effect, V1's wet channel = a **mono external FX loop** on
the R channel (elegant: defers "which effect", total flexibility, fits V1.2 custom):
- `L IN → L OUT` = main mono signal (dry, buffered).
- Granular loop → mixed into L OUT (STOMP LEFT = engage/freeze).
- `R OUT` = **FX send**, `R IN` = **FX return** = the external wet channel.
- **Routing IN/BOTH/LOOP** = what feeds the send (dry / dry+loop / loop only).
- **STOMP RIGHT** = engage/bypass the FX loop (return into the mix).
- Tradeoff: patch is **mono** (L=audio, R=FX loop). Fine for V1.
Open Qs before building: does the loop go straight to L OUT AND to the send, or only via
the loop? return-level knob? any small internal reverb too, or is the FX loop the whole wet?
STATUS: **standby** (user paused build).

## Proposed Magician architecture (to confirm with user before building)
1. **Capture**: Looper `length_edit=on` (head+length+reverse+speed) — the "matter".
   (Optionally a Granular in parallel for grain-freeze scanning.)
2. **Transmute**: a chain of switchable/dosable modifiers — pitch (octave/stretch),
   reverse, granular fragmenting, filter, degrade/aliaser, random re-roll per pass.
3. **Haunt**: into reverb (reuse The Star's Plate/Ghostverb/Hall) + optional Reverse Delay.
4. Stomps: capture/record · freeze/hold · transmute (trigger a modifier burst) · bypass.

Reusable bricks: The Star reverbs (`zoia_lib/backend/The_Star.bin`), La Papesse
pitch-descending / reverse / random (`High_Priestess.bin`).

## Changing head/length live — reset/glitch handling
In **moodz**, `start_position` + `loop_length` are driven **directly** by MIDI CC with
**NO `restart_playback`, no Trigger/Comparator/S&H, no fade** — i.e. it changes head/
length live and handles nothing. So either ZOIA applies it cleanly natively, or moodz
just tolerates clicks. **Decide on device:** if live head/length changes glitch/click,
THEN add (a) a re-`restart_playback` trigger so it jumps to the new window immediately,
(b) a short fade/envelope to de-click boundaries, (c) a clamp so `start_position +
loop_length ≤ recorded buffer`. Do NOT add these blind — only if the device test shows
they're needed (the reference patch does none of them).

## Open items / cautions
- **Looper record/play is finicky** — prototype the control scheme and TEST ON DEVICE
  early (momentary vs latching, first-pass-length, auto-loop, overdub clear-on-hold).
- Find Christopher's (ZOIA educator) looper explanation for the exact CV logic.
- Watch CPU (Granular 17 + Looper + reverbs).
- Build to the USER's exact module/routing spec; verify byte-exact; sync to SD
  (`/Volumes/DELUGE/ZOIA/`, see memory [[zoia-sd-sync]]). Don't overwrite the user's files.

Sources: [Empress ZOIA](https://empresseffects.com/products/zoia) ·
[ZOIA Cheatsheet](https://sensai7.github.io/ZOIACheatsheet/) ·
[DL4 Looper patch (Patchstorage)](https://patchstorage.com/dl4-looper-4-button-performance-setup/)
