import os
import shutil
import tempfile
import unittest

from zoia_lib.interface.ZOIALibrarian_sd import ZOIALibrarianSD


class TestSD(unittest.TestCase):
    """This class is responsible for testing the file operations that
    back the SD card tab. They are exercised through the static helper so
    that no Qt application is needed.
    """

    def setUp(self):
        self.sd = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.sd, ignore_errors=True)

    def _write(self, name, content):
        with open(os.path.join(self.sd, name), "w") as f:
            f.write(content)

    def _contents(self):
        found = {}
        for name in os.listdir(self.sd):
            with open(os.path.join(self.sd, name)) as f:
                found[name] = f.read()
        return found

    def test_swap_same_filename(self):
        """Swaps two slots holding files of the same name.

        os.rename overwrites its destination on POSIX, so renaming in
        place used to leave a single file behind and empty the other slot.
        """

        self._write("001_zoia_Foo.bin", "SLOT-1")
        self._write("002_zoia_Foo.bin", "SLOT-2")

        ZOIALibrarianSD._rename_via_temp(
            self.sd,
            [("001_zoia_Foo.bin", "002_zoia_Foo.bin"),
             ("002_zoia_Foo.bin", "001_zoia_Foo.bin")],
        )

        self.assertEqual(
            self._contents(),
            {"001_zoia_Foo.bin": "SLOT-2", "002_zoia_Foo.bin": "SLOT-1"},
        )

    def test_swap_different_filenames(self):
        """Swaps two slots holding differently named files."""

        self._write("003_zoia_Hierophant.bin", "HIEROPHANT")
        self._write("007_zoia_Star.bin", "STAR")

        ZOIALibrarianSD._rename_via_temp(
            self.sd,
            [("003_zoia_Hierophant.bin", "007_zoia_Hierophant.bin"),
             ("007_zoia_Star.bin", "003_zoia_Star.bin")],
        )

        self.assertEqual(
            self._contents(),
            {"007_zoia_Hierophant.bin": "HIEROPHANT", "003_zoia_Star.bin": "STAR"},
        )

    def test_rotate_three_slots(self):
        """Rotates three slots, where every destination is another
        move's source.
        """

        for slot, content in (("000", "A"), ("001", "B"), ("002", "C")):
            self._write("{}_zoia_Patch.bin".format(slot), content)

        ZOIALibrarianSD._rename_via_temp(
            self.sd,
            [("000_zoia_Patch.bin", "001_zoia_Patch.bin"),
             ("001_zoia_Patch.bin", "002_zoia_Patch.bin"),
             ("002_zoia_Patch.bin", "000_zoia_Patch.bin")],
        )

        self.assertEqual(
            self._contents(),
            {
                "001_zoia_Patch.bin": "A",
                "002_zoia_Patch.bin": "B",
                "000_zoia_Patch.bin": "C",
            },
        )

    def test_no_temporary_files_left_behind(self):
        """The staging names must not survive the rename batch."""

        self._write("001_zoia_Foo.bin", "SLOT-1")
        self._write("002_zoia_Foo.bin", "SLOT-2")

        ZOIALibrarianSD._rename_via_temp(
            self.sd,
            [("001_zoia_Foo.bin", "002_zoia_Foo.bin"),
             ("002_zoia_Foo.bin", "001_zoia_Foo.bin")],
        )

        self.assertEqual(
            [name for name in os.listdir(self.sd) if name.startswith("tmp_rename_")],
            [],
        )


if __name__ == "__main__":
    unittest.main()
