#!/usr/bin/env python3
"""
WHAT THIS DOES
---------------
PC save files (.es3) wrap every top-level field like:
    "KEY" : { "__type": "...", "value": <data> }
Switch save files (.dat) are a small binary header (4 null bytes +
a varint length prefix) followed by *flat* JSON with no type
wrapper, null-padded to a fixed buffer size.

Everything BELOW the top level is identical between platforms
(confirmed by direct comparison) -- only the top-level key names
differ, and only in a few files (Settings.es3 most notably renames
several fields outright, e.g. ENDINGS -> mitaEnd). Data day-files
mostly just change ALLCAPS -> camelCase, with a few renames
(STATUS -> stats, MIDOKUCOUNT -> midokumushi, LOOPCOUNT -> loop,
EVENTHISTORY -> eventsHistory).

This script:
  1. Reads each .es3 file as plain JSON (it parses cleanly).
  2. Strips the __type/value wrapper from each top-level field.
  3. Renames each top-level key per the mapping tables below.
  4. Packs the result into the Switch .dat binary format.
  5. If a matching Switch .dat already exists in this folder, reuses
     its file size and merges in Switch-only fields (like
     vibrationType) that don't exist on PC, otherwise picks a sane
     default buffer size.
"""

import json
import os
import re
import sys

# ---------------------------------------------------------------
# Key mapping tables: PC (.es3, ALLCAPS) -> Switch (.dat, camelCase)
# ---------------------------------------------------------------

SETTINGS_MAP = {
    "RESOLUTION":          "resolution",
    "UNLOCKEDZIP":         "unLockedZip",
    "ANIMATIONKETHISTORY": None,  # no confirmed Switch equivalent seen
    "IMAGEHISTORY":        "imageHistory",
    "ENDINGS":             "mitaEnd",
    "HAISHINSPEED":        "haishinSpeed",
    "SE":                  "seVolume",
    "BGM":                 "bgmVolume",
    "LANG":                "languageType",
}

# Switch-only fields with no PC equivalent -- preserved from the
# existing Switch save (if present) rather than overwritten.
SETTINGS_SWITCH_ONLY = ["vibrationType"]

DAY_MAP = {
    "IS500MIL":         "is500mil",
    "IS300MIL":         "is300mil",
    "IS150MIL":         "is150mil",
    "ISOPENGINGA":      "isOpenGinga",
    "LOVEDIARY":        "loveDiary",
    "KYUUSICOUNT":      "kyuusiCount",
    "ISSHUROKUED":      "isShurokued",
    "BEFOREWRISTCUT":   "beforeWristCut",
    "ISHAKKYO":         "isHakkyo",
    "ISWRISTCUT":       "isWristCut",
    "WISHLIST":         "wishlist",
    "ISGEDATSU":        "isGedatsu",
    "ISHORROR":         "isHorror",
    "ISHAPPAOK":        "isHappaOK",
    "FIRSTDATE":        "firstDate",
    "TRAUMA":           "trauma",
    "ISHEARTRAUMA":     "isHearTrauma",
    "ISJUNCHO":         "isJuncho",
    "USEDNETAS":        "usedNetas",
    "HAVINGNETAS":      "havingNetas",
    "STATUS":           "stats",
    "PSYCHECOUNT":      "psycheCount",
    "MIDOKUCOUNT":      "midokumushi",
    "LOOPCOUNT":        "loop",
    "DAYACTIONHISTORY": "dayActionHistory",
    "EVENTHISTORY":     "eventsHistory",
    "POKETTERHISTORY":  "poketterHistory",
    "JINEHISTORY":      "jineHistory",
}

DEFAULT_SETTINGS_BUFFER = 16384
DEFAULT_DAY_BUFFER = 245760


def encode_varint(n):
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            break
    return bytes(out)


def decode_varint(data, offset):
    result = 0
    shift = 0
    pos = offset
    while True:
        b = data[pos]
        result |= (b & 0x7F) << shift
        pos += 1
        if not (b & 0x80):
            break
        shift += 7
    return result, pos


def read_switch_dat(path):
    """Return (flat_json_dict, total_buffer_size) for an existing .dat file."""
    raw = open(path, "rb").read()
    # 4 null bytes, then varint length, then JSON
    length, json_start = decode_varint(raw, 4)
    json_bytes = raw[json_start:json_start + length]
    return json.loads(json_bytes.decode("utf-8")), len(raw)


def write_switch_dat(path, flat_dict, buffer_size):
    json_bytes = json.dumps(flat_dict, separators=(",", ":")).encode("utf-8")
    payload = b"\x00\x00\x00\x00" + encode_varint(len(json_bytes)) + json_bytes
    if len(payload) > buffer_size:
        # grow to the next 4KB boundary rather than truncate data
        buffer_size = ((len(payload) // 4096) + 1) * 4096
        print(f"  ! payload bigger than expected buffer, growing to {buffer_size} bytes")
    padded = payload + b"\x00" * (buffer_size - len(payload))
    with open(path, "wb") as f:
        f.write(padded)


def convert_file(es3_path, key_map, switch_only_keys, existing_dat_path, default_buffer):
    with open(es3_path, encoding="utf-8") as f:
        parsed = json.load(f)

    flat = {}
    unmapped = []
    for key, wrapper in parsed.items():
        value = wrapper["value"] if isinstance(wrapper, dict) and "value" in wrapper else wrapper
        if key in key_map:
            target = key_map[key]
            if target is not None:
                flat[target] = value
        else:
            unmapped.append(key)

    buffer_size = default_buffer
    if existing_dat_path and os.path.exists(existing_dat_path):
        try:
            existing_flat, buffer_size = read_switch_dat(existing_dat_path)
            for k in switch_only_keys:
                if k in existing_flat:
                    flat[k] = existing_flat[k]
        except Exception as e:
            print(f"  ! couldn't read existing Switch file for buffer sizing ({e}), using default size")

    return flat, buffer_size, unmapped


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(script_dir, "NSWindose")
    os.makedirs(out_dir, exist_ok=True)

    es3_files = sorted(f for f in os.listdir(script_dir) if f.lower().endswith(".es3"))
    if not es3_files:
        print("No .es3 files found next to this script. Put it in the same folder as your PC save files.")
        return

    print(f"Found {len(es3_files)} .es3 file(s). Output will go to: {out_dir}\n")

    for fname in es3_files:
        es3_path = os.path.join(script_dir, fname)
        base = fname[:-4]  # strip .es3
        dat_name = base + ".dat"
        existing_dat_path = os.path.join(script_dir, dat_name)
        out_path = os.path.join(out_dir, dat_name)

        if base.lower() == "settings":
            key_map, switch_only, default_buffer = SETTINGS_MAP, SETTINGS_SWITCH_ONLY, DEFAULT_SETTINGS_BUFFER
        else:
            key_map, switch_only, default_buffer = DAY_MAP, [], DEFAULT_DAY_BUFFER

        print(f"Converting {fname} -> NSWindose/{dat_name}")
        try:
            flat, buffer_size, unmapped = convert_file(
                es3_path, key_map, switch_only, existing_dat_path, default_buffer
            )
        except Exception as e:
            print(f"  ! FAILED to convert {fname}: {e}")
            continue

        if unmapped:
            print(f"  ! WARNING: unmapped PC keys found (not carried over): {unmapped}")
            print(f"    These fields exist in your PC save but have no known Switch mapping yet.")

        write_switch_dat(out_path, flat, buffer_size)
        print(f"  OK -> {len(json.dumps(flat))} bytes of JSON in a {buffer_size}-byte buffer\n")

    print("Done. Back up your real Switch save before replacing anything with these files.")


if __name__ == "__main__":
    main()
