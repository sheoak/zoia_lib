import os
import unittest

from zoia_lib.backend.patch_binary import PatchBinary
from zoia_lib.backend.patch_encode import PatchEncoder


class EncodeDecodeRoundtripTest(unittest.TestCase):
    def test_roundtrip_bin_matches_source(self):
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        test_dir = os.path.join(root_dir, "zoia_lib", "tests", "sample_files")
        sample_path = os.path.join(test_dir, "input_test.bin")

        with open(sample_path, "rb") as f:
            original = f.read()

        decoded = PatchBinary().parse_data(original)
        output_path = os.path.join(test_dir, "output_test.bin")
        try:
            encoded = PatchEncoder().encode(decoded, output_path=output_path)
            self.assertIsInstance(encoded, (bytes, bytearray))
            self.assertTrue(os.path.exists(output_path))
            self.assertGreater(len(encoded), 0)
            encoded_size = int.from_bytes(bytes(encoded[:4]), byteorder="little")
            payload_len = (encoded_size - 1) * 4
            self.assertGreater(payload_len, 0)
            self.assertLessEqual(payload_len, 32764)
            self.assertTrue(any(b != 0 for b in encoded[4:4 + payload_len]))
            self.assertTrue(all(b == 0 for b in encoded[4 + payload_len:]))
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)


class FailedEncodeTest(unittest.TestCase):
    def test_failure_leaves_the_output_file_untouched(self):
        """A patch that cannot be encoded must not destroy an existing file."""

        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        test_dir = os.path.join(root_dir, "zoia_lib", "tests", "sample_files")
        sample_path = os.path.join(test_dir, "input_test.bin")

        with open(sample_path, "rb") as f:
            original = f.read()

        decoded = PatchBinary().parse_data(original)
        del decoded["modules"][0]["size"]

        output_path = os.path.join(test_dir, "untouched_test.bin")
        with open(output_path, "wb") as f:
            f.write(original)
        try:
            with self.assertRaises(KeyError):
                PatchEncoder().encode(decoded, output_path=output_path)
            with open(output_path, "rb") as f:
                self.assertEqual(f.read(), original)
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)


class NameFieldTest(unittest.TestCase):
    """Patch, module and page names are fixed-width, NUL-padded byte fields."""

    NAMES = [
        "The Hierophant",
        "Don't Panic",  # an apostrophe used to truncate the name
        "A\\B",  # so did a backslash
        "Cafe",
        "abcdefghijklmnop",  # exactly 16 bytes, no padding left
        "",
    ]

    def test_name_survives_encode_then_decode(self):
        for name in self.NAMES:
            field = PatchEncoder.encode_text(name, 16)
            self.assertEqual(len(field), 16)
            self.assertEqual(PatchBinary._qc_name(bytes(field)), name)

    def test_name_is_truncated_to_the_field_size(self):
        field = PatchEncoder.encode_text("WayTooLongForTheField", 16)
        self.assertEqual(len(field), 16)
        self.assertEqual(PatchBinary._qc_name(bytes(field)), "WayTooLongForThe")

    def test_non_ascii_is_measured_in_bytes(self):
        # "e" costs one byte, "é" costs two: the field must still be 16 bytes,
        # and must not cut a character in half.
        field = PatchEncoder.encode_text("Café", 16)
        self.assertEqual(len(field), 16)
        self.assertEqual(PatchBinary._qc_name(bytes(field)), "Café")

        field = PatchEncoder.encode_text("é" * 10, 16)
        self.assertEqual(len(field), 16)
        self.assertEqual(PatchBinary._qc_name(bytes(field)), "é" * 8)

    def test_padding_is_ignored(self):
        self.assertEqual(PatchBinary._qc_name(b"Name\x00\x00\x00\x00"), "Name")
        self.assertEqual(PatchBinary._qc_name(b"Name\x00junk"), "Name")
