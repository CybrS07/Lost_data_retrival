import os
import platform

# ---------------------------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------------------------
if platform.system() == "Windows":
    drive = r"\\.\G:"
else:
    # IMPORTANT: To recover DELETED files, pass the raw partition (e.g., /dev/sdb1)
    # If testing on existing files, pass the folder path.
    drive = "/home/cybes07/Desktop/Lost_data_retrival/Test/"

OUTPUT_DIR = "recovered"
os.makedirs(OUTPUT_DIR, exist_ok=True)

size = 512  # Read sector size
rcvd = 0    # Counter for recovered files
MAX_SIZE = 50 * 1024 * 1024  # 50 MB max limit per file

# Updated file signatures (Added MP4 header/footer and standard formats)
FORMATS = [
    # JPEG Signatures
    ("jpg", b"\xff\xd8\xff\xdb", b"\xff\xd9"),
    ("jpg", b"\xff\xd8\xff\xe0", b"\xff\xd9"),
    ("jpg", b"\xff\xd8\xff\xee", b"\xff\xd9"),
    ("jpg", b"\xff\xd8\xff\xe1", b"\xff\xd9"),
    # PNG
    ("png", b"\x89PNG\r\n\x1a\n", b"IEND\xae\x42\x60\x82"),
    # MP4 Video (ftypisom, ftypmp42, ftypMSNV)
    ("mp4", b"\x00\x00\x00\x18ftyp", None),
    ("mp4", b"\x00\x00\x00\x1cftyp", None),
    ("mp4", b"\x00\x00\x00\x20ftyp", None),
    # MP3 Audio
    ("mp3", b"\xff\xfb", None),
    ("mp3", b"\xff\xf3", None),
    ("mp3", b"\xff\xf2", None),
    ("mp3", b"ID3", None),
]

RIFF_TAGS = {b"WAVE": "wav", b"AVI ": "avi"}

# ---------------------------------------------------------------------------
# RECOVERY LOGIC
# ---------------------------------------------------------------------------
if os.path.isdir(drive):
    files_to_scan = [os.path.join(root, f) for root, _, files in os.walk(drive) for f in files]
else:
    files_to_scan = [drive]

for target_path in files_to_scan:
    try:
        fileD = open(target_path, "rb")
    except (PermissionError, FileNotFoundError):
        print(f"Failed to access '{target_path}'. Run with sudo if scanning raw devices.")
        continue

    offs = 0
    buffer = b""

    while True:
        chunk = fileD.read(size)
        if not chunk:
            break

        buffer += chunk
        handled = False

        # 1. Check Standard Formats (JPG, PNG, MP4, MP3)
        for ext, start, end in FORMATS:
            found = buffer.find(start)
            if found >= 0:
                out_path = f"{OUTPUT_DIR}/{rcvd}_{ext}.{ext}"
                fileN = open(out_path, "wb")
                
                # Write data starting from the matched header signature
                data = buffer[found:]
                written = len(data)
                
                print(f"==== Found {ext.upper()} at sector offset {offs} ====")

                while True:
                    if end:
                        bfind = data.find(end)
                        if bfind >= 0:
                            fileN.write(data[: bfind + len(end)])
                            break
                        else:
                            fileN.write(data)
                    else:
                        fileN.write(data)
                        if written >= MAX_SIZE:
                            break

                    data = fileD.read(size)
                    if not data:
                        break
                    written += len(data)

                fileN.close()
                print(f"==== Recovered: {out_path} ====\n")
                rcvd += 1
                buffer = b""
                handled = True
                break

        # 2. Check RIFF Formats (WAV, AVI)
        if not handled:
            found = buffer.find(b"RIFF")
            if found >= 0 and len(buffer) >= found + 12:
                tag = buffer[found + 8 : found + 12]
                if tag in RIFF_TAGS:
                    ext = RIFF_TAGS[tag]
                    out_path = f"{OUTPUT_DIR}/{rcvd}_{ext}.{ext}"
                    fileN = open(out_path, "wb")
                    
                    data = buffer[found:]
                    written = len(data)
                    print(f"==== Found {ext.upper()} at sector offset {offs} ====")

                    while True:
                        fileN.write(data)
                        if written >= MAX_SIZE:
                            break
                        data = fileD.read(size)
                        if not data:
                            break
                        written += len(data)

                    fileN.close()
                    print(f"==== Recovered: {out_path} ====\n")
                    rcvd += 1
                    buffer = b""

        # Keep buffer small to prevent memory bloat
        if len(buffer) > size * 4:
            buffer = buffer[-size:]

        offs += 1

    fileD.close()

print(f"Scan completed. Check the '{OUTPUT_DIR}' directory.")