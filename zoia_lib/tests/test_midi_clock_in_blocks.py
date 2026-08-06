"""Midi Clock In's optional outputs were named one block apart.

`reset_out` sat at position 2 and `run_out` at 3, but the module has three options
that each reveal one block - clock_out, run_out and divider - and max_blocks is 4.
Counted over a corpus of 2337 patches, what patches actually source from:

    run_out enabled, divider disabled     blocks 0 and 2
    run_out disabled, divider enabled     blocks 0 and 3
    both enabled                          blocks 0, 2 and 3
    clock_out enabled                     block 1

So block 2 is run_out, and block 3 is the divided clock the `divider` option
reveals - which the file did not name at all, while naming a `reset_out` the module
does not have.

_calc_blocks was already right: it indexes the block list by entry number and lines
opt[1] (run_out) up with entry 2 and opt[2] (divider) with entry 3. Only the names
were wrong, which is exactly the kind of error that costs an afternoon - I wired a
patch's MIDI-sync gate to what the file called run_out and got the divider output.
"""

import json
import unittest

from zoia_lib.backend.utilities import meipass

with open(meipass("zoia_lib/common/schemas/ModuleIndex.json")) as f:
    MOD = json.load(f)

MIDI_CLOCK_IN = "82"


class TestMidiClockInBlocks(unittest.TestCase):
    def positions(self):
        return {n: m["position"] for n, m in MOD[MIDI_CLOCK_IN]["blocks"].items()}

    def test_run_out_is_block_two(self):
        self.assertEqual(self.positions()["run_out"], 2)

    def test_the_divider_output_is_block_three_and_is_named(self):
        self.assertEqual(self.positions()["divider_out"], 3)

    def test_there_is_no_reset_out(self):
        self.assertNotIn("reset_out", self.positions())

    def test_the_default_and_the_clock_are_unchanged(self):
        pos = self.positions()
        self.assertEqual(pos["quarter_out"], 0)
        self.assertEqual(pos["clock_out"], 1)

    def test_one_block_per_option_plus_the_default(self):
        """Three options each reveal one block, so four in total."""
        entry = MOD[MIDI_CLOCK_IN]
        revealing = [o for o in entry["options"] if o != "beat_modifier"]
        self.assertEqual(len(revealing), 3)
        self.assertEqual(len(entry["blocks"]), 4)
        self.assertEqual(entry["max_blocks"], 4)
        self.assertEqual(entry["default_blocks"], 1)

    def test_positions_are_contiguous_and_all_outputs(self):
        pos = self.positions()
        self.assertEqual(sorted(pos.values()), [0, 1, 2, 3])
        for name, meta in MOD[MIDI_CLOCK_IN]["blocks"].items():
            self.assertEqual(meta["type"], "cv_out", name)


class TestCalcBlocksStillLinesUp(unittest.TestCase):
    """_calc_blocks indexes by entry number, so the renaming must not move anything."""

    def setUp(self):
        from zoia_lib.backend.patch_binary import PatchBinary

        self.pb = PatchBinary()

    def _clock(self, clock_out="disabled", run_out="disabled", divider="disabled"):
        return {"mod_idx": 82, "version": 0,
                "options": {"clock_out": clock_out, "run_out": run_out,
                            "divider": divider, "beat_modifier": "1"}}

    def test_nothing_enabled(self):
        self.assertEqual(list(self.pb._calc_blocks(self._clock())), ["quarter_out"])

    def test_run_out_enabled(self):
        blocks = self.pb._calc_blocks(self._clock(run_out="enabled"))
        self.assertEqual(list(blocks), ["quarter_out", "run_out"])
        self.assertEqual(blocks["run_out"]["position"], 2)

    def test_divider_enabled(self):
        blocks = self.pb._calc_blocks(self._clock(divider="enabled"))
        self.assertEqual(list(blocks), ["quarter_out", "divider_out"])
        self.assertEqual(blocks["divider_out"]["position"], 3)

    def test_everything_enabled(self):
        blocks = self.pb._calc_blocks(
            self._clock(clock_out="enabled", run_out="enabled", divider="enabled"))
        self.assertEqual(list(blocks),
                         ["quarter_out", "clock_out", "run_out", "divider_out"])


if __name__ == "__main__":
    unittest.main()
