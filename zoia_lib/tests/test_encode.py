import os
import unittest

from zoia_lib.backend.patch_binary import PatchBinary
from zoia_lib.backend.patch_encode import PatchEncoder
from zoia_lib.common import errors

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "sample_files")

# A module record is its 10-word header plus its parameters, its saved data and
# a 16-byte name field.
MODULE_OVERHEAD_WORDS = 14


def _sample(name):
    with open(os.path.join(SAMPLE_DIR, name), "rb") as f:
        return f.read()


def _repair_module_sizes(patch):
    """Set each module's declared size to the length its record really needs.

    input_test.bin declares one word per module, which no real record can be,
    so nothing built from it can be written back. Correcting the sizes gives a
    patch the encoder can express, which is what the round-trip needs.
    """

    for module in patch["modules"]:
        module["size"] = (
            MODULE_OVERHEAD_WORDS
            + module["params"]
            + len(module.get("saved_data") or []) // 4
        )
    # Its colour words are text read as integers, and re-encoding them lands a
    # zero where the parser looks for colours. Colour handling is not what these
    # tests are about, so give it something the palette knows.
    patch["colors"] = [1] * len(patch["modules"])
    return patch


class EncodeDecodeRoundtripTest(unittest.TestCase):
    def test_encoding_is_idempotent(self):
        """Decoding what we encoded and encoding it again must not drift.

        Byte-exactness against a hardware-written file is covered elsewhere;
        what this pins down is that the two halves of the codec agree with each
        other, so an edit cannot change bytes it was not asked to change.
        """

        patch = _repair_module_sizes(PatchBinary().parse_data(_sample("input_test.bin")))

        first = bytes(PatchEncoder().encode(patch))
        second = bytes(PatchEncoder().encode(PatchBinary().parse_data(first)))

        self.assertEqual(len(first), 32768)
        self.assertEqual(first, second)

    def test_output_is_padded_with_zeroes(self):
        patch = _repair_module_sizes(PatchBinary().parse_data(_sample("input_test.bin")))
        encoded = bytes(PatchEncoder().encode(patch))

        payload_len = (int.from_bytes(encoded[:4], byteorder="little") - 1) * 4
        self.assertGreater(payload_len, 0)
        self.assertLessEqual(payload_len, 32764)
        self.assertTrue(any(b != 0 for b in encoded[4:4 + payload_len]))
        self.assertTrue(all(b == 0 for b in encoded[4 + payload_len:]))

    def test_output_file_is_written(self):
        patch = _repair_module_sizes(PatchBinary().parse_data(_sample("input_test.bin")))
        output_path = os.path.join(SAMPLE_DIR, "output_test.bin")
        try:
            encoded = PatchEncoder().encode(patch, output_path=output_path)
            self.assertIsInstance(encoded, (bytes, bytearray))
            with open(output_path, "rb") as f:
                self.assertEqual(f.read(), bytes(encoded))
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)


class ModuleSizeTest(unittest.TestCase):
    """A record rebuilt to a different length than it declares is refused.

    The pedal walks the modules by the size in each header, so writing a record
    that overruns its own declaration moves every field after it. input_test.bin
    declares one word per module and is the shortest possible case of this.
    """

    def test_declared_size_that_cannot_be_honoured_is_refused(self):
        patch = PatchBinary().parse_data(_sample("input_test.bin"))
        self.assertEqual(patch["modules"][0]["size"], 1)

        with self.assertRaises(errors.BinaryError):
            PatchEncoder().encode(patch)

    def test_a_honourable_size_encodes(self):
        patch = _repair_module_sizes(PatchBinary().parse_data(_sample("input_test.bin")))
        self.assertTrue(bytes(PatchEncoder().encode(patch)))

    def test_one_word_too_few_is_refused(self):
        patch = _repair_module_sizes(PatchBinary().parse_data(_sample("input_test.bin")))
        patch["modules"][0]["size"] -= 1

        with self.assertRaises(errors.BinaryError):
            PatchEncoder().encode(patch)

    def test_a_size_with_room_to_spare_is_padded_not_refused(self):
        """Only a size too small to hold the record is a problem.

        The saved-data block is padded out to whatever the declared size leaves,
        so a record can always grow into a larger declaration - which is why the
        check only ever fires one way.
        """

        patch = _repair_module_sizes(PatchBinary().parse_data(_sample("input_test.bin")))
        patch["modules"][0]["size"] += 3

        encoded = bytes(PatchEncoder().encode(patch))
        self.assertEqual(PatchBinary().parse_data(encoded)["modules"][0]["size"],
                         patch["modules"][0]["size"])


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
