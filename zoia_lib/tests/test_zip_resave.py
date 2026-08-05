import io
import json
import os
import shutil
import tempfile
import unittest
import zipfile

from zoia_lib.backend.patch_save import PatchSave
from zoia_lib.common import errors


def _zip(entries):
    """Builds a .zip in memory holding the given {name: bytes}."""

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in entries.items():
            z.writestr(name, data)
    return buf.getvalue()


def _meta(idx="999001", title="Zip patch"):
    return {
        "id": idx,
        "title": title,
        "files": [{"filename": "{}.zip".format(idx), "id": idx}],
        "created_at": "2020-01-01T00:00:00+00:00",
        "updated_at": "2020-01-01T00:00:00+00:00",
        "revision": "1.0",
        "author": {"name": "tester"},
    }


class ZipResaveTest(unittest.TestCase):
    """A .zip already in the library must still take in a changed binary.

    save_to_backend extracts the archive into back_path/temp and reads each
    entry back with `open(file)` - a bare name from os.listdir, resolved
    against the working directory. Every entry therefore raised
    FileNotFoundError, which `except FileNotFoundError or errors.SavingError`
    swallowed, so `diff` stayed False and the method ended on
    SavingError(title, 503) - "already saved". check_for_updates reads that as
    "same binary, notes only", writes the fresh upstream metadata over the
    local copy and marks the update done, so the new binary is lost and the
    patch looks up to date.
    """

    def setUp(self):
        self.back_path = tempfile.mkdtemp()
        self.save = PatchSave()
        self.save.back_path = self.back_path

    def tearDown(self):
        shutil.rmtree(self.back_path, ignore_errors=True)

    def _stored_binaries(self, idx="999001"):
        folder = os.path.join(self.back_path, idx)
        if not os.path.isdir(folder):
            return []
        return sorted(f for f in os.listdir(folder) if f.endswith(".bin"))

    def test_a_changed_binary_is_saved_on_the_second_download(self):
        first = _zip({"999001.bin": b"\x01" * 32768})
        self.save.save_to_backend((first, _meta()))
        self.assertEqual(self._stored_binaries(), ["999001.bin"])

        second = _zip({"999001.bin": b"\x02" * 32768})
        self.save.save_to_backend((second, _meta()))

        # The changed binary lands as a new version rather than being dropped.
        self.assertGreater(len(self._stored_binaries()), 1, self._stored_binaries())

    def test_an_unchanged_archive_is_still_reported_as_already_saved(self):
        same = _zip({"999001.bin": b"\x03" * 32768})
        self.save.save_to_backend((same, _meta()))

        with self.assertRaises(errors.SavingError) as caught:
            self.save.save_to_backend((same, _meta()))
        self.assertEqual(caught.exception.args[1], 503)

    def test_the_temporary_directory_is_cleaned_up(self):
        self.save.save_to_backend((_zip({"999001.bin": b"\x04" * 32768}), _meta()))
        self.assertFalse(os.path.isdir(os.path.join(self.back_path, "temp")))

    def test_the_metadata_is_written_beside_the_binary(self):
        self.save.save_to_backend((_zip({"999001.bin": b"\x05" * 32768}), _meta()))
        with open(os.path.join(self.back_path, "999001", "999001.json")) as f:
            self.assertEqual(json.load(f)["title"], "Zip patch")
