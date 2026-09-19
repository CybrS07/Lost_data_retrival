import os

out_dir = "recover"
os.makedirs(out_dir, exist_ok=True)

signatures = {
    "jpg": {"header": b"\xff\xd8\xff", "footer": b"\xff\xd9", "footer_len": 2},
    "png": {"header": b"\x89PNG\r\n\x1a\n", "footer": b"\x49\x45\x4e\x44\xae\x42\x60\x82", "footer_len": 8},
    "mp3": {"header": b"ID3", "footer": None, "max_size": 10 * 1024 * 1024},
}

drive = r"\\.\C:"
sector_size = 512
rcvd = 0

with open(drive, "rb") as fileD:
    sector_num = 0

    while True:
        # Seek strictly to sector boundaries
        fileD.seek(sector_num * sector_size)
        sector = fileD.read(sector_size)
        if not sector:
            break

        for ext, sig in signatures.items():
            header_offset = sector.find(sig["header"])
            if header_offset >= 0:
                abs_header_pos = (sector_num * sector_size) + header_offset
                out_path = os.path.join(out_dir, f"{rcvd}.{ext}")

                # Read forward from sector start
                fileD.seek(sector_num * sector_size)
                data = bytearray()
                recovering = True

                while recovering:
                    chunk = fileD.read(sector_size)
                    if not chunk:
                        break
                    data.extend(chunk)

                    if sig["footer"]:
                        # Look for footer after header alignment
                        relative_data = data[header_offset:]
                        footer_pos = relative_data.find(sig["footer"])
                        if footer_pos >= 0:
                            clean_file = relative_data[: footer_pos + sig["footer_len"]]
                            with open(out_path, "wb") as f_out:
                                f_out.write(clean_file)
                            recovering = False
                    else:
                        if len(data) >= sig["max_size"]:
                            clean_file = data[header_offset : sig["max_size"]]
                            with open(out_path, "wb") as f_out:
                                f_out.write(clean_file)
                            recovering = False

                print(f"==== Recovered {out_path} at offset {hex(abs_header_pos)} ====")
                rcvd += 1

                # Advance to next sector after header
                break

        sector_num += 1