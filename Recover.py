"""
file_recovery.py

Simple multi-format file-carving tool for raw disk recovery.

Scans a drive (or a disk image file) for known file signatures and
saves every match it finds into an output folder. Works even after a
file's filesystem entry has been deleted, since it reads the drive's
raw bytes directly instead of going through the filesystem.

Supported formats: JPEG (raw / JFIF / Adobe / Exif), JPEG 2000,
QOI, PNG, WAV, AVI, MP3.

Runs on Windows, Linux, and macOS -- just check DRIVE_PATH below.
"""

import os
import platform

# ---------------------------------------------------------------------------
# Settings -- edit these to match your situation
# ---------------------------------------------------------------------------

if platform.system() == "Windows":
    DRIVE_PATH = r"\\.\G:"      # Windows: raw device path (the drive letter to scan)
else:
    DRIVE_PATH = "/dev/sdb"     # Linux/macOS: block device path (needs root)
                                # macOS tip: "/dev/rdiskN" is the faster raw variant

OUTPUT_DIR = "recovered"        # Folder where recovered files are saved
CHUNK_SIZE = 512                # Bytes read per pass (disk sector size)
MAX_SIZE = 20 * 1024 * 1024     # Size cap for formats with no clear end marker

# ---------------------------------------------------------------------------
# Known file signatures: (name, extension, start bytes, end bytes)
# If end bytes is None, the format has no reliable end marker, so we
# just save up to MAX_SIZE bytes instead of searching for one.
# ---------------------------------------------------------------------------

FORMATS = [
    ("JPEG (raw)",      "jpg", b"\xff\xd8\xff\xdb", b"\xff\xd9"),
    ("JPEG (JFIF)",     "jpg", b"\xff\xd8\xff\xe0", b"\xff\xd9"),
    ("JPEG (Adobe)",    "jpg", b"\xff\xd8\xff\xee", b"\xff\xd9"),
    ("JPEG (Exif)",     "jpg", b"\xff\xd8\xff\xe1", b"\xff\xd9"),
    ("JPEG 2000",       "jp2", b"\x00\x00\x00\x0c\x6a\x50\x20\x20", None),
    ("JPEG 2000 (raw)", "j2c", b"\xff\x4f\xff\x51", None),
    ("QOI",              "qoi", b"qoif", b"\x00\x00\x00\x00\x00\x00\x00\x01"),
    ("PNG",               "png", b"\x89PNG\r\n\x1a\n", b"IEND\xae\x42\x60\x82"),
    ("MP3",               "mp3", b"\xff\xfb", None),
    ("MP3",               "mp3", b"\xff\xf3", None),
    ("MP3",               "mp3", b"\xff\xf2", None),
    ("MP3 (ID3 tag)",    "mp3", b"ID3", None),
]

# WAV and AVI both start with "RIFF", then 4 size bytes, then a type tag.
# The size bytes are unpredictable, so these are checked separately
# instead of being added to FORMATS as a fixed pattern.
RIFF_TAGS = {b"WAVE": "wav", b"AVI ": "avi"}


# ---------------------------------------------------------------------------
# Saving a recovered file
# ---------------------------------------------------------------------------

def save_until_marker(disk, data, end_bytes, out_path):
    """Write bytes to out_path until end_bytes is found."""
    with open(out_path, "wb") as f:
        while True:
            pos = data.find(end_bytes)
            if pos != -1:
                f.write(data[:pos + len(end_bytes)])
                return
            f.write(data)
            data = disk.read(CHUNK_SIZE)
            if not data:
                return  # reached end of drive without finding the marker


def save_fixed_amount(disk, data, amount, out_path):
    """Write exactly `amount` bytes to out_path, reading more as needed."""
    with open(out_path, "wb") as f:
        while amount > 0 and data:
            piece = data[:amount]
            f.write(piece)
            amount -= len(piece)
            data = disk.read(CHUNK_SIZE) if amount > 0 else b""


# ---------------------------------------------------------------------------
# Main scan loop
# ---------------------------------------------------------------------------

def recover_files():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    counts = {}

    with open(DRIVE_PATH, "rb") as disk:
        data = disk.read(CHUNK_SIZE)

        while data:
            handled = False

            # Check the plain fixed-signature formats
            for name, ext, start, end in FORMATS:
                pos = data.find(start)
                if pos != -1:
                    counts[ext] = counts.get(ext, 0) + 1
                    out_path = os.path.join(OUTPUT_DIR, f"{ext}_{counts[ext]}.{ext}")
                    print(f"Found {name} -> {out_path}")

                    if end:
                        save_until_marker(disk, data[pos:], end, out_path)
                    else:
                        save_fixed_amount(disk, data[pos:], MAX_SIZE, out_path)
                    handled = True
                    break

            # Check for RIFF-based formats (WAV / AVI) if nothing else matched
            if not handled:
                pos = data.find(b"RIFF")
                if pos != -1 and len(data) >= pos + 12:
                    tag = data[pos + 8:pos + 12]
                    if tag in RIFF_TAGS:
                        ext = RIFF_TAGS[tag]
                        counts[ext] = counts.get(ext, 0) + 1
                        out_path = os.path.join(OUTPUT_DIR, f"{ext}_{counts[ext]}.{ext}")
                        print(f"Found {ext.upper()} -> {out_path}")
                        save_fixed_amount(disk, data[pos:], MAX_SIZE, out_path)

            data = disk.read(CHUNK_SIZE)

    print(f"\nDone. Recovered files saved in '{OUTPUT_DIR}/'.")


if __name__ == "__main__":
    try:
        recover_files()
    except PermissionError:
        print("Permission denied. Run as Administrator (Windows) or with sudo (Linux/macOS).")
    except FileNotFoundError:
        print(f"Could not open '{DRIVE_PATH}'. Edit DRIVE_PATH at the top of the script.")