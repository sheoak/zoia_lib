import json
import os
import shutil
import tempfile
import unittest

from zoia_lib.backend.patch_export import PatchExport
from zoia_lib.common import errors


class ExportSlotValidationTest(unittest.TestCase):
    """A slot outside 0-63 has to be refused, not quietly renamed.

    The bound used to read `slot >= 10 < 64`, a chained comparison that Python
    reads as `(slot >= 10) and (10 < 64)` - so `slot >= 10`, and the branch
    raising ExportingError was unreachable for every slot above nine. Slot 100
    produced 0100_zoia_.bin, which the pedal does not load.
    """

    def setUp(self):
        self.back_path = tempfile.mkdtemp()
        self.dest = tempfile.mkdtemp()
        self.export = PatchExport()
        self.export.back_path = self.back_path

        os.makedirs(os.path.join(self.back_path, "12345"))
        self.patch = "12345.bin"
        with open(os.path.join(self.back_path, "12345", self.patch), "wb") as f:
            f.write(b"\x00" * 32768)
        with open(os.path.join(self.back_path, "12345", "12345.json"), "w") as f:
            json.dump({"files": [{"filename": "my patch.bin"}]}, f)

    def tearDown(self):
        shutil.rmtree(self.back_path, ignore_errors=True)
        shutil.rmtree(self.dest, ignore_errors=True)

    def _exported_name(self, slot):
        target = os.path.join(self.dest, "bank-{}".format(slot))
        os.makedirs(target, exist_ok=True)
        self.export.export_patch_bin(self.patch, target, slot)
        return os.listdir(target)

    def test_a_slot_over_63_is_refused(self):
        for slot in (64, 100, 999):
            with self.assertRaises(errors.ExportingError, msg=slot):
                self._exported_name(slot)

    def test_every_valid_slot_is_padded_to_three_digits(self):
        for slot in (0, 9, 10, 63):
            names = self._exported_name(slot)
            self.assertEqual(len(names), 1)
            self.assertTrue(
                names[0].startswith("{:03d}_".format(slot)),
                "slot {} exported as {}".format(slot, names[0]),
            )

    def test_a_negative_slot_keeps_the_name_undecorated(self):
        names = self._exported_name(-1)
        self.assertEqual(len(names), 1)
        self.assertFalse(names[0][:3].isdigit(), names[0])
