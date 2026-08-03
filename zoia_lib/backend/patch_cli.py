"""Command-line bridge between ZOIA .bin patches and editable JSON.

This tool exists so that an AI agent (e.g. Claude Code) or a human can edit
ZOIA patches as plain, well-structured JSON text and write them back to the
binary format the pedal reads.

Workflow
--------
    python -m zoia_lib.backend.patch_cli decode  my_patch.bin  my_patch.json
    # ...edit my_patch.json (by hand or with an AI agent)...
    python -m zoia_lib.backend.patch_cli encode  my_patch.json out.bin

Other commands
--------------
    info       Human-readable summary of a .bin (modules, cpu, pages, wiring).
    roundtrip  Study command: decode -> encode -> compare bytes, and report
               how faithfully the current encoder reproduces the original.

It wraps the existing PatchBinary (parser) and PatchEncoder (writer). The JSON
it emits is exactly the dict produced by PatchBinary.parse_data, so `encode`
can read back anything `decode` wrote.

NOTE ON FIDELITY: the encoder is not yet byte-exact. See `roundtrip` and the
accompanying skill (.claude/skills/zoia-patch-edit) for the current caveats.
"""

import argparse
import json
import sys

from zoia_lib.backend.patch_binary import PatchBinary
from zoia_lib.backend.patch_encode import PatchEncoder


def _read_bin(path):
    with open(path, "rb") as f:
        return f.read()


def _summary_lines(patch):
    """Return a list of human-readable lines describing a parsed patch."""
    meta = patch.get("meta", {})
    lines = [
        "name:        {}".format(patch.get("name")),
        "modules:     {}".format(meta.get("n_modules", len(patch.get("modules", [])))),
        "connections: {}".format(meta.get("n_connections", len(patch.get("connections", [])))),
        "pages:       {}".format(meta.get("n_pages", len(patch.get("pages", [])))),
        "starred:     {}".format(meta.get("n_starred", len(patch.get("starred", [])))),
        "total cpu:   {}".format(meta.get("cpu")),
        "",
        "Modules:",
    ]
    for m in patch.get("modules", []):
        lines.append(
            "  [{number}] {name} (idx {mod_idx}, {category})"
            "  page {page}  blocks {position}  color {color}".format(
                number=m.get("number"),
                name=m.get("name"),
                mod_idx=m.get("mod_idx"),
                category=m.get("category"),
                page=m.get("page"),
                position=m.get("position"),
                color=m.get("color"),
            )
        )
    if patch.get("connections"):
        lines.append("")
        lines.append("Connections (source -> destination @ strength):")
        for c in patch["connections"]:
            lines.append(
                "  {} -> {}  @ {}".format(
                    c.get("source"), c.get("destination"), c.get("strength")
                )
            )
    return lines


def cmd_decode(args):
    raw = _read_bin(args.input)
    patch = PatchBinary().parse_data(raw)
    out_path = args.output or (args.input.rsplit(".", 1)[0] + ".json")
    with open(out_path, "w") as f:
        json.dump(patch, f, indent=2)
    print("Decoded {} -> {}".format(args.input, out_path))
    print("\n".join(_summary_lines(patch)))
    return 0


def cmd_encode(args):
    with open(args.input) as f:
        patch = json.load(f)
    out_path = args.output or (args.input.rsplit(".", 1)[0] + ".bin")
    data = PatchEncoder().encode(
        patch, output_path=out_path, param_order_mode=args.param_order
    )
    print("Encoded {} -> {} ({} bytes)".format(args.input, out_path, len(data)))
    print(
        "NOTE: the encoder is not yet byte-exact; run `roundtrip` on a source "
        ".bin to see current fidelity before trusting a device import."
    )
    return 0


def cmd_info(args):
    patch = PatchBinary().parse_data(_read_bin(args.input))
    print("\n".join(_summary_lines(patch)))
    return 0


def cmd_roundtrip(args):
    """Decode then re-encode a .bin and report how faithfully it reproduces."""
    original = _read_bin(args.input)
    patch = PatchBinary().parse_data(original)
    encoded = bytes(PatchEncoder().encode(patch, param_order_mode=args.param_order))

    print("original bytes: {}".format(len(original)))
    print("encoded bytes:  {}".format(len(encoded)))

    overlap = min(len(original), len(encoded))
    diffs = [i for i in range(overlap) if original[i] != encoded[i]]
    print("differing bytes (in overlap): {}".format(len(diffs)))
    if len(original) != len(encoded):
        print("LENGTH MISMATCH: {} vs {}".format(len(original), len(encoded)))

    # group consecutive diff offsets into ranges for readability
    ranges = []
    for i in diffs:
        if ranges and i == ranges[-1][1] + 1:
            ranges[-1][1] = i
        else:
            ranges.append([i, i])
    if ranges:
        print("diff ranges (offset: orig -> enc):")
        for s, e in ranges[: args.max_ranges]:
            print(
                "  {:>6}-{:<6} {} -> {}".format(
                    s, e + 1, original[s : e + 1].hex(), encoded[s : e + 1].hex()
                )
            )
        if len(ranges) > args.max_ranges:
            print("  ... {} more ranges".format(len(ranges) - args.max_ranges))

    # can the encoded output be parsed back?
    try:
        reparsed = PatchBinary().parse_data(encoded)
        semantic_ok = reparsed == patch
        print("re-decodes without error: YES")
        print("re-decoded dict equals original dict: {}".format(semantic_ok))
    except Exception as e:  # noqa: BLE001 - study/report only
        print("re-decodes without error: NO ({}: {})".format(type(e).__name__, e))

    byte_exact = not diffs and len(original) == len(encoded)
    print("\nVERDICT: {}".format("byte-exact" if byte_exact else "NOT byte-exact"))
    return 0 if byte_exact else 1


def build_parser():
    p = argparse.ArgumentParser(
        prog="zoia-patch",
        description="Convert ZOIA .bin patches to/from editable JSON.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    d = sub.add_parser("decode", help="binary .bin -> editable .json")
    d.add_argument("input", help="path to the .bin patch")
    d.add_argument("output", nargs="?", help="output .json (default: <input>.json)")
    d.set_defaults(func=cmd_decode)

    e = sub.add_parser("encode", help="edited .json -> binary .bin")
    e.add_argument("input", help="path to the .json patch")
    e.add_argument("output", nargs="?", help="output .bin (default: <input>.bin)")
    e.add_argument(
        "--param-order",
        default="order",
        choices=["order", "saved"],
        help="parameter serialization mode passed to PatchEncoder",
    )
    e.set_defaults(func=cmd_encode)

    i = sub.add_parser("info", help="print a human-readable patch summary")
    i.add_argument("input", help="path to the .bin patch")
    i.set_defaults(func=cmd_info)

    r = sub.add_parser("roundtrip", help="study encoder fidelity for a .bin")
    r.add_argument("input", help="path to the .bin patch")
    r.add_argument("--param-order", default="order", choices=["order", "saved"])
    r.add_argument("--max-ranges", type=int, default=20, help="diff ranges to show")
    r.set_defaults(func=cmd_roundtrip)

    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
