import os
import shutil
import tempfile
import unittest
import unittest.mock as mock

from zoia_lib.backend.patch_save import PatchSave


def _bin(path, marker=b"\x00"):
    with open(path, "wb") as f:
        f.write(marker * 32768)


class VersionImportStrayFileTest(unittest.TestCase):
    """A version history often holds something that is not a patch.

    Those entries used to be handed to save_to_backend anyway. The failure was
    then reported under the name of the *folder*, because a version import
    derives its title from the directory - so the user was told
    "tmpXXXX failed" with no way to tell which file was the problem. And when
    the stray file sorted after the patches it took a code path raising a
    single-argument SavingError, whose message the error handler picked apart
    with str(e).split("(")[1] - an IndexError inside the error handler, which
    killed the import thread with no message box at all.
    """

    def setUp(self):
        self.back_path = tempfile.mkdtemp()
        self.source = tempfile.mkdtemp()
        self.save = PatchSave()
        self.save.back_path = self.back_path

    def tearDown(self):
        shutil.rmtree(self.back_path, ignore_errors=True)
        shutil.rmtree(self.source, ignore_errors=True)

    def test_a_stray_file_does_not_kill_the_import(self):
        _bin(os.path.join(self.source, "001_zoia_a.bin"), b"\x01")
        _bin(os.path.join(self.source, "002_zoia_b.bin"), b"\x02")
        with open(os.path.join(self.source, "000_notes.txt"), "w") as f:
            f.write("not a patch")

        imported, fails, errs = self.save.import_to_backend(self.source, True)

        self.assertEqual(imported, 2)
        self.assertEqual(fails, 0)
        self.assertEqual(errs, [])

    def test_a_stray_file_sorting_after_the_patches_is_also_skipped(self):
        """The stray used to be processed first or last depending on its name,
        and only one of the two orders crashed."""

        _bin(os.path.join(self.source, "001_zoia_a.bin"), b"\x01")
        _bin(os.path.join(self.source, "002_zoia_b.bin"), b"\x02")
        with open(os.path.join(self.source, "zzz_readme.txt"), "w") as f:
            f.write("not a patch")

        imported, fails, errs = self.save.import_to_backend(self.source, True)

        self.assertEqual(imported, 2)
        self.assertEqual(fails, 0)

    def test_the_count_reflects_what_was_imported(self):
        for n in range(1, 4):
            _bin(os.path.join(self.source, "00{}_zoia_p.bin".format(n)), bytes([n]))

        imported, fails, errs = self.save.import_to_backend(self.source, True)

        self.assertEqual(imported, 3)
        self.assertEqual(fails, 0)

    def test_a_failure_names_the_file_and_survives_a_one_argument_error(self):
        """SavingError is raised with one argument in some branches and two in
        others. The handler used to read the name out of str(e) by splitting on
        a parenthesis, which the single-argument form does not have - an
        IndexError inside the error handler, escaping import_to_backend and
        killing the worker thread with no message box.
        """

        _bin(os.path.join(self.source, "001_zoia_a.bin"), b"\x01")
        _bin(os.path.join(self.source, "002_zoia_b.bin"), b"\x02")

        from zoia_lib.common import errors

        with mock.patch.object(
            PatchSave, "save_to_backend", side_effect=errors.SavingError("a title")
        ):
            imported, fails, errs = self.save.import_to_backend(self.source, True)

        self.assertEqual(imported, 0)
        self.assertEqual(fails, 2)
        self.assertEqual(sorted(errs), ["001_zoia_a.bin", "002_zoia_b.bin"])
        self.assertNotIn(os.path.basename(self.source), errs)
