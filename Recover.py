import os

out_dir = "recover"
os.makedirs(out_dir, exist_ok=True)

signatures = {
    "jpg": {"header": b"\xff\xd8\xff", "footer": b"\xff\xd9"},
    "png": {"header": b"\x89PNG\r\n\x1a\n", "footer": b"IEND\xae\x42\x60\x82"},
    "mp3": {"header": b"ID3", "footer": None, "max_size": 10 * 1024 * 1024},
}

drive = "/dev/nvme0n1p2"
sector_size = 512
rcvd = 0

with open(drive, "rb") as fileD:
    sector_num = 0

    while True:
        fileD.seek(sector_num * sector_size)
        sector = fileD.read(sector_size)
        if not sector:
            break

        for ext, sig in signatures.items():
            header_offset = sector.find(sig["header"])
            if header_offset >= 0:
                abs_header_pos = (sector_num * sector_size) + header_offset
                
                # Start reading from exact header position
                fileD.seek(abs_header_pos)
                data = bytearray()
                recovering = True

                while recovering:
                    chunk = fileD.read(sector_size)
                    if not chunk:
                        break
                    data.extend(chunk)

                    if sig["footer"]:
                        footer_pos = data.find(sig["footer"])
                        if footer_pos >= 0:
                            clean_file = data[: footer_pos + len(sig["footer"])]
                            # Only save if file is larger than just header/footer
                            if len(clean_file) > 100:
                                out_path = os.path.join(out_dir, f"{rcvd}.{ext}")
                                with open(out_path, "wb") as f_out:
                                    f_out.write(clean_file)
                                print(f"==== Successfully recovered {out_path} ({len(clean_file)} bytes) ====")
                                rcvd += 1
                            recovering = False
                    else:
                        if len(data) >= sig["max_size"]:
                            out_path = os.path.join(out_dir, f"{rcvd}.{ext}")
                            with open(out_path, "wb") as f_out:
                                f_out.write(data)
                            print(f"==== Recovered {out_path} ====")
                            rcvd += 1
                            recovering = False
                break

        sector_num += 1