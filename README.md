# File Recovery Tool

A small Python script that recovers files from a raw disk or disk image,
even after they've been deleted. It works by scanning the drive's raw
bytes for known file "magic number" signatures — a technique called
**file carving**.

## How it works (in short)

When a file is deleted, the filesystem usually just removes its index
entry — the actual bytes often stay on disk until something else
overwrites them. This script ignores the filesystem and reads the
drive directly in small chunks, looking for the fixed byte patterns
that mark the start (and sometimes the end) of known file types.

## Requirements

- Python 3
- Administrator (Windows) or root (Linux/macOS) privileges — raw disk
  access is a protected operation
- Read access to the target drive or disk image

## Usage

1. Open `file_recovery.py`. `DRIVE_PATH` is set automatically based on
   your OS, but you'll need to point it at your actual target:
   - **Windows**: raw device path, e.g. `r"\\.\G:"` (a drive letter)
   - **Linux**: block device path, e.g. `"/dev/sdb"`
   - **macOS**: raw device path, e.g. `"/dev/rdisk2"`
   - You can also point it at a disk image file, e.g. `"disk.img"`
2. Run it:
   ```bash
   python file_recovery.py
   ```
   On Windows, use an **Administrator** terminal. On Linux/macOS, run
   with `sudo`.
3. Recovered files appear in the `recovered/` folder, named like
   `jpg_1.jpg`, `png_1.png`, `mp3_1.mp3`, etc. The folder is created
   automatically.

## Supported formats

| Format | Extension | How the end is detected |
|---|---|---|
| JPEG (raw / JFIF / Adobe / Exif) | `.jpg` | End marker (`FF D9`) |
| PNG | `.png` | End marker (`IEND` chunk) |
| QOI | `.qoi` | End marker |
| JPEG 2000 | `.jp2` / `.j2c` | Size cap (no reliable end marker) |
| WAV | `.wav` | Size cap |
| AVI | `.avi` | Size cap |
| MP3 (with or without ID3 tag) | `.mp3` | Size cap |

## Configuration options

All at the top of the file:

| Variable | Purpose | Default |
|---|---|---|
| `DRIVE_PATH` | Drive or image file to scan | auto-set per OS |
| `OUTPUT_DIR` | Folder for recovered files | `recovered` |
| `CHUNK_SIZE` | Bytes read per pass (sector size) | `512` |
| `MAX_SIZE` | Cap used for formats with no end marker | `20 MB` |

## Code structure

- **`FORMATS`** — a simple list of `(name, extension, start bytes, end bytes)`
  for every format that has a fixed, exact starting signature.
- **`RIFF_TAGS`** — WAV and AVI both start with `RIFF`, then 4 bytes of
  file size, then a type tag (`WAVE` or `AVI `). Since those size
  bytes vary per file, these two formats are checked separately rather
  than added to `FORMATS` as one fixed pattern.
- **`save_until_marker()`** — keeps reading and writing until an exact
  end-of-file marker turns up.
- **`save_fixed_amount()`** — writes a fixed number of bytes; used for
  formats that don't have a reliable end marker.
- **`recover_files()`** — the main loop: reads the drive chunk by
  chunk, checks each chunk against every known signature, and saves
  any match it finds.

## Known limitations (kept simple on purpose)

- **Size cap, not exact size**: JPEG 2000, WAV, AVI, and MP3 don't get
  parsed for their real length — the script just writes up to
  `MAX_SIZE` bytes. For WAV/AVI this is a simplification: the RIFF
  header actually *does* contain an exact size field, but reading it
  makes the code more complex, so this version just caps the length
  instead. Recovered files in these formats may be padded with extra
  trailing data.
- **Signatures split across chunk reads can be missed**: if a marker
  happens to fall exactly on the boundary between two 512-byte reads,
  it may not be detected.
- **First match in the list wins per chunk**: if two different formats'
  signatures happen to appear in the same 512-byte chunk, only the one
  listed first in `FORMATS` is recovered from that chunk.
- **Some JPEG variants share a shortened signature**: matching uses a
  4-byte prefix (e.g. `FF D8 FF E1` for Exif) rather than the full,
  more specific signature, to keep the matching logic simple.

## Disclaimer

This tool reads raw data directly from a storage device. Always work
on a **copy or image of the drive**, not the original, when doing real
data recovery — this avoids the risk of accidentally overwriting the
very data you're trying to recover.