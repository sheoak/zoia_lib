"""Delay Line's max_time values, checked against what patches choose.

An option's index in its list is the byte written to the file, so a list in the
wrong order silently gives a module the wrong setting. Nothing raises: the patch
encodes, round-trips byte-exact and loads, and the delay is simply on the wrong
range.

The order below was settled by asking what kind of patch picks which byte, over a
corpus of 2337 patches:

    byte 0   chorus / flanger / vibrato      delay / echo / looper
    0                            22                            9
    1                            10                           65
    2                             0                           53
    3                             1                           43
    4                             0                           19
    5                             0                           62

A chorus reaches for the short range and a looper for the long one, so byte 0 is
100 ms and byte 5 is 16 s. Read the other way round - the file's old order - a
delay would be choosing the one-second range nine times and the hundred-millisecond
range sixty-two, and no chorus would ever pick 100 ms.
"""

import json
import unittest

from zoia_lib.backend.utilities import meipass

with open(meipass("zoia_lib/common/schemas/ModuleIndex.json")) as f:
    MOD = json.load(f)

DELAY_LINE = "13"


class TestMaxTimeOrder(unittest.TestCase):
    def test_shortest_range_is_first(self):
        self.assertEqual(MOD[DELAY_LINE]["options"]["max_time"][0], "100ms")

    def test_ranges_ascend(self):
        self.assertEqual(
            MOD[DELAY_LINE]["options"]["max_time"],
            ["100ms", "1s", "2s", "4s", "8s", "16s"],
        )

    def test_other_options_keep_their_order(self):
        """byte 1 is tap_tempo_in: it alone tracks the visible block count.

        Over the corpus, byte 1 at 0 always gives three blocks and at 1 always
        gives four, with no exceptions - which is what fixes the position of every
        option in the list.
        """
        opts = list(MOD[DELAY_LINE]["options"])
        self.assertEqual(opts[0], "max_time")
        self.assertEqual(opts[1], "tap_tempo_in")


class TestOptionListsAreOrdered(unittest.TestCase):
    """Where a list is plainly a scale, it should read in order.

    This is the check that would have caught it. Only lists whose every entry
    parses as a duration are considered, so unordered option sets are left alone.
    """

    UNITS = {"ms": 0.001, "s": 1.0}

    @classmethod
    def _seconds(cls, value):
        for suffix, scale in cls.UNITS.items():
            if value.endswith(suffix):
                head = value[: -len(suffix)]
                try:
                    return float(head) * scale
                except ValueError:
                    return None
        return None

    def test_duration_lists_ascend(self):
        for mod_idx, entry in MOD.items():
            for name, values in (entry.get("options") or {}).items():
                if not isinstance(values, list) or len(values) < 3:
                    continue
                secs = [self._seconds(v) for v in values if isinstance(v, str)]
                if len(secs) != len(values) or any(s is None for s in secs):
                    continue
                self.assertEqual(
                    secs,
                    sorted(secs),
                    "%s (idx %s) option %s is out of order: %s"
                    % (entry["name"], mod_idx, name, values),
                )


if __name__ == "__main__":
    unittest.main()
