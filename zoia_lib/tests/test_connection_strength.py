"""Connection strength is stored logarithmically, at 2000 raw units to a decade.

    percent = 100 * 10 ** ((strength_raw - 10000) / 2000)

Read as raw / 100 - as this library did - a connection the pedal applies at 1% is
reported as "60". The error is invisible at full strength, because raw 10000 divided
by 100 is also 100, which is what makes it so easy to miss: a patch written that way
has every full connection right and every attenuated one between a hundred and a
thousand times too quiet.

The scale was read off the hardware at three points - raw 11200 displays 398.1%, raw
9886 displays 87.7%, raw 10000 displays 100% - and the corpus agrees: of 198612
connections, 81.2% sit at raw 10000, and the next most common values are 9398, 8000,
8796, 9750 and 7398, which are exactly 50%, 10%, 25%, 75% and 5%.
"""

import unittest

from zoia_lib.backend.patch_binary import PatchBinary


class TestStrengthScale(unittest.TestCase):
    # raw -> percent, as shown on the pedal
    KNOWN = {
        0: 0.0,
        7398: 5.0,
        8000: 10.0,
        8796: 25.0,
        9398: 50.0,
        9750: 75.0,
        9886: 87.7,
        10000: 100.0,
        10602: 200.0,
        11200: 398.1,
    }

    def test_known_points(self):
        for raw, percent in self.KNOWN.items():
            self.assertAlmostEqual(
                PatchBinary.strength_percent(raw), percent, delta=0.05,
                msg="raw %d" % raw,
            )

    def test_unity_is_ten_thousand(self):
        self.assertEqual(PatchBinary.strength_percent(10000), 100.0)
        self.assertEqual(PatchBinary.strength_raw(100), 10000)

    def test_a_decade_is_two_thousand_raw(self):
        for raw in (8000, 9000, 10000):
            lower = PatchBinary.strength_percent(raw)
            self.assertAlmostEqual(
                PatchBinary.strength_percent(raw + 2000),
                lower * 10,
                delta=max(0.02, lower * 0.1),
            )

    def test_round_trips(self):
        for raw in list(self.KNOWN) + [8500, 9088, 9556, 10250, 11000]:
            if raw == 0:
                continue
            back = PatchBinary.strength_raw(PatchBinary.strength_percent(raw))
            self.assertEqual(back, raw, "raw %d did not survive" % raw)

    def test_the_ceiling(self):
        """The largest value the corpus holds is raw 11200, and it is common."""
        self.assertAlmostEqual(PatchBinary.strength_percent(11200), 398.1, delta=0.05)

    def test_zero_stays_zero(self):
        self.assertEqual(PatchBinary.strength_percent(0), 0.0)
        self.assertEqual(PatchBinary.strength_raw(0), 0)


class TestNotTheOldLinearReading(unittest.TestCase):
    """The values a raw = percent * 100 encoder used to produce."""

    def test_what_the_old_scale_really_asked_for(self):
        for written, applied in ((6, 0.002), (20, 0.01), (35, 0.056), (60, 1.0)):
            self.assertAlmostEqual(
                PatchBinary.strength_percent(written * 100), applied,
                delta=max(0.001, applied * 0.02),
                msg="writing %d%% as raw %d" % (written, written * 100),
            )

    def test_full_strength_was_right_by_coincidence(self):
        self.assertEqual(PatchBinary.strength_percent(100 * 100), 100.0)


if __name__ == "__main__":
    unittest.main()
