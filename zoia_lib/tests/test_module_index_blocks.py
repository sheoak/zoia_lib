"""Block positions in ModuleIndex.json, checked against how patches really wire.

A block's position is its connection index, so getting one wrong does not raise:
the patch encodes, loads, and silently does nothing. Each case below was found by
counting connections over a corpus of 2337 patches - a block used as a connection
source has to be an output, and one used as a destination has to be an input.
"""

import json
import unittest

from zoia_lib.backend.utilities import meipass

with open(meipass("zoia_lib/common/schemas/ModuleIndex.json")) as f:
    MOD = json.load(f)


def positions(mod_idx):
    out = {}
    for name, meta in MOD[str(mod_idx)]["blocks"].items():
        out[name] = meta["position"]
    return out


class TestSequencerOutputs(unittest.TestCase):
    """key_input is a MIDI mode, not two blocks.

    Their entries used to sit at 34 and 35, pushing all eight outputs to 36-43.
    A one-track Sequencer sources from block 34 in 2351 corpus connections and
    from 36 in none; an eight-track one uses exactly 34 through 41.
    """

    def test_outputs_start_at_34(self):
        pos = positions(4)
        for i in range(1, 9):
            self.assertEqual(pos["out_track_%d" % i], 33 + i)

    def test_key_input_is_not_a_block(self):
        pos = positions(4)
        self.assertNotIn("key_input_note", pos)
        self.assertNotIn("key_input_gate", pos)

    def test_steps_gate_and_queue_are_unchanged(self):
        pos = positions(4)
        self.assertEqual(pos["step_1"], 0)
        self.assertEqual(pos["step_32"], 31)
        self.assertEqual(pos["gate_in"], 32)
        self.assertEqual(pos["queue_start"], 33)


class TestTremoloOutputs(unittest.TestCase):
    """control picks one of rate, tap_tempo_in and direct.

    direct shares depth's slot rather than owning one, so depth and both outputs
    used to be a block late. Blocks 5 and 6 are used as connection sources 164
    times, and block 4 is a destination under control=rate and control=tap_tempo,
    which is depth's condition rather than direct's.
    """

    def test_depth_and_outputs(self):
        pos = positions(41)
        self.assertEqual(pos["depth"], 4)
        self.assertEqual(pos["audio_out_L"], 5)
        self.assertEqual(pos["audio_out_R"], 6)

    def test_direct_shares_depths_slot(self):
        pos = positions(41)
        self.assertEqual(pos["direct"], pos["depth"])

    def test_rate_and_tap_keep_their_own_slots(self):
        pos = positions(41)
        self.assertEqual(pos["rate"], 2)
        self.assertEqual(pos["tap_tempo_in"], 3)


class TestAudioInSwitchInputs(unittest.TestCase):
    """Inputs 9 to 14 were numbered two high, leaving 8 and 9 empty.

    That also made audio_input_13/14 collide with audio_input_15/16. Blocks 8 and
    9 are used as destinations in the corpus, so they exist.
    """

    def test_inputs_are_contiguous_from_zero(self):
        pos = positions(33)
        for i in range(1, 17):
            self.assertEqual(pos["audio_input_%d" % i], i - 1)

    def test_select_and_output_follow(self):
        pos = positions(33)
        self.assertEqual(pos["in_select"], 16)
        self.assertEqual(pos["audio_output"], 17)


class TestNoAccidentalCollisions(unittest.TestCase):
    """No two blocks share a position unless the module makes them exclusive."""

    # mod_idx -> the set of block names that legitimately share one slot
    EXCLUSIVE = {41: {"direct", "depth"}}

    def test_positions_are_unique(self):
        for mod_idx, entry in MOD.items():
            seen = {}
            for name, meta in entry["blocks"].items():
                pos = meta["position"]
                for p in pos if isinstance(pos, list) else [pos]:
                    if p in seen:
                        allowed = self.EXCLUSIVE.get(int(mod_idx), set())
                        self.assertTrue(
                            {name, seen[p]} <= allowed,
                            "%s (idx %s): %s and %s both at position %d"
                            % (entry["name"], mod_idx, seen[p], name, p),
                        )
                    seen[p] = name


class TestNoUnexplainedGaps(unittest.TestCase):
    """Positions run from 0 without holes, except where the pedal leaves one.

    The three pushbuttons really do start at 1: their cv_output is used as a
    connection source 17195 times across the corpus and block 0 never is. That is
    behaviour rather than an error, so it is listed rather than fixed.
    """

    STARTS_AT_ONE = {15: "Pushbutton", 97: "Euro Pushbutton 1", 98: "Euro Pushbutton 2"}

    def test_no_holes(self):
        for mod_idx, entry in MOD.items():
            held = set()
            for meta in entry["blocks"].values():
                pos = meta["position"]
                held.update(pos if isinstance(pos, list) else [pos])
            if not held:
                continue
            expected = set(range(max(held) + 1))
            if int(mod_idx) in self.STARTS_AT_ONE:
                expected.discard(0)
            self.assertEqual(
                held,
                expected,
                "%s (idx %s) is missing position(s) %s"
                % (entry["name"], mod_idx, sorted(expected - held)),
            )


if __name__ == "__main__":
    unittest.main()


class TestCalcBlocksStaysInStep(unittest.TestCase):
    """_calc_blocks indexes the block list by entry number, not by position.

    So editing a module's block table silently breaks it: removing the two
    key_input entries once made every Sequencer with more than a few tracks raise
    IndexError, which cost eight patches in the corpus their decode. This walks the
    branch that broke.
    """

    def setUp(self):
        from zoia_lib.backend.patch_binary import PatchBinary

        self.pb = PatchBinary()

    def _sequencer(self, steps, tracks, queue="off", key="off"):
        return {
            "mod_idx": 4,
            "version": 0,
            "options": {
                "number_of_steps": steps,
                "num_of_tracks": tracks,
                "restart_jack": queue,
                "behavior": "loop",
                "key_input": key,
                "number_of_pages": 1,
            },
        }

    def test_eight_tracks_and_thirty_two_steps(self):
        blocks = self.pb._calc_blocks(self._sequencer(32, 8))
        self.assertEqual(len(blocks), 32 + 1 + 8)
        for i in range(1, 9):
            self.assertIn("out_track_%d" % i, blocks)
            self.assertEqual(blocks["out_track_%d" % i]["position"], 33 + i)

    def test_one_track_gives_one_output(self):
        blocks = self.pb._calc_blocks(self._sequencer(3, 1))
        self.assertEqual(list(blocks), ["step_1", "step_2", "step_3", "gate_in", "out_track_1"])

    def test_queue_start_is_added_when_asked(self):
        blocks = self.pb._calc_blocks(self._sequencer(2, 1, queue="on"))
        self.assertIn("queue_start", blocks)

    def test_key_input_adds_no_block(self):
        plain = self.pb._calc_blocks(self._sequencer(4, 2))
        keyed = self.pb._calc_blocks(self._sequencer(4, 2, key="active"))
        self.assertEqual(list(plain), list(keyed))

    def test_no_branch_indexes_past_its_block_list(self):
        """Whatever the options, no branch may run off the end of its own list.

        ValueError is a module's own guard against an impossible option set and is
        expected; IndexError and KeyError mean the branch and the block table have
        drifted apart.
        """
        import itertools

        for mod_idx, entry in MOD.items():
            opts = entry.get("options") or {}
            if not opts:
                continue
            keys = list(opts)
            for combo in itertools.islice(itertools.product(*(opts[k] for k in keys)), 60):
                module = {
                    "mod_idx": int(mod_idx),
                    "version": 0,
                    "options": dict(zip(keys, combo)),
                }
                try:
                    self.pb._calc_blocks(module)
                except ValueError:
                    pass          # the module refusing an impossible option set
                except (IndexError, KeyError) as exc:
                    self.fail(
                        "%s (idx %s) with %s: %s: %s"
                        % (entry["name"], mod_idx, module["options"],
                           type(exc).__name__, exc)
                    )
