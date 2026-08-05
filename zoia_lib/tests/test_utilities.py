import unittest

from zoia_lib.backend.utilities import slot_number


class SlotNumberTest(unittest.TestCase):
    """Cards hold more than the 64 slots the pedal loads from."""

    def test_a_slot_file_gives_its_number(self):
        self.assertEqual(slot_number("000_zoia_deep_water.bin"), 0)
        self.assertEqual(slot_number("051_zoia_jungle 2.bin"), 51)
        self.assertEqual(slot_number("020_zoia_.bin"), 20)

    def test_a_file_outside_the_slots_gives_none(self):
        # Real names from a card in daily use: patches copied by hand, backups,
        # renames left behind. Reading a slot number out of these used to raise
        # ValueError and stop an export before it began.
        for name in (
            "High_Priestess.bin",
            "Magician_MkII_base_FROZEN.bin",
            "REVTEST.bin",
            "The_Star.bin",
        ):
            self.assertIsNone(slot_number(name), name)

    def test_a_number_past_the_last_slot_is_still_read(self):
        """Whether 111 is a usable slot is the caller's business, not ours."""

        self.assertEqual(slot_number("111_zoia_ALTERNEATH_V5.bin"), 111)

    def test_edge_cases(self):
        self.assertIsNone(slot_number(""))
        self.assertIsNone(slot_number("_zoia_no_number.bin"))
        self.assertIsNone(slot_number("12a_zoia_almost.bin"))
