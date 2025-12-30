#!/usr/bin/env python3
"""
Resume/finish iCloud Photos Export – Date Fixer

- Uses existing output NEW_IMAGES_SORTED/IMAGES as "already done"
- Creates NEW_IMAGES_SORTED_FINISHING/IMAGES for remaining items
- Reads CSVs again but only processes filenames not already done
- Uses ExifTool stay_open for speed

Requires:
- ExifTool on PATH
- pip install tqdm
"""

import csv
import subprocess
import shutil
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from tqdm import tqdm

EXPORT_FOLDER_SUBSTRING = "iCloud Photos"
DONE_OUTPUT_DIRNAME = "NEW_IMAGES_SORTED"
FINISH_OUTPUT_DIRNAME = "NEW_IMAGES_SORTED_FINISHING"
VIDEO_EXTS = {".mov", ".mp4", ".m4v", ".avi", ".mts", ".m2ts", ".3gp", ".3gpp"}
CSV_REQUIRED_COLUMNS = {"imgName", "originalCreationDate"}

def parse_icloud_date(date_str: str) -> str:
    s = (date_str or "").strip()
    if not s:
        raise ValueError("empty date")
    parts = s.split()
    if parts and parts[-1].isalpha() and len(parts[-1]) <= 5:
        s = " ".join(parts[:-1])
    dt = datetime.strptime(s, "%A %B %d,%Y %I:%M %p")
    return dt.strftime("%Y:%m:%d %H:%M:%S")

class ExifToolStayOpen:
    def __init__(self):
        try:
            self.p = subprocess.Popen(
                ["exiftool", "-stay_open", "True", "-@", "-"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1,
            )
        except FileNotFoundError:
            raise SystemExit("ExifTool not found on PATH. Install ExifTool and ensure 'exiftool -ver' works.")

    def run_args(self, args_list: list[str]) -> bool:
        assert self.p.stdin and self.p.stdout
        for a in args_list:
            self.p.stdin.write(a + "\n")
        self.p.stdin.write("-execute\n")
        self.p.stdin.flush()
        while True:
            line = self.p.stdout.readline()
            if not line:
                return False
            if "{ready}" in line:
                return True

    def close(self):
        try:
            if self.p.stdin:
                self.p.stdin.write("-stay_open\nFalse\n")
                self.p.stdin.write("-execute\n")
                self.p.stdin.flush()
        except Exception:
            pass
        try:
            self.p.terminate()
        except Exception:
            pass

def find_export_folders(root: Path) -> list[Path]:
    return [p for p in root.iterdir() if p.is_dir() and EXPORT_FOLDER_SUBSTRING in p.name]

def iter_csv_files(root: Path) -> list[Path]:
    return [p for p in root.rglob("*.csv") if p.is_file()]

def read_done_names(done_images_dir: Path) -> set[str]:
    if not done_images_dir.exists():
        return set()
    return {p.name for p in done_images_dir.iterdir() if p.is_file()}

def load_skipped_names(previous_errors_dir: Path) -> set[str]:
    """
    Optional: skip things already logged as failures previously.
    We read first column only from these CSVs if present.
    """
    skipped = set()
    for fname in ["CANNOT_BE_FOUND.csv", "BAD_DATE.csv", "EXIFTOOL_FAILED.csv"]:
        p = previous_errors_dir / fname
        if not p.exists():
            continue
        try:
            with open(p, newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                # skip header if present
                header = next(reader, None)
                for row in reader:
                    if row and row[0]:
                        skipped.add(row[0].strip())
        except Exception:
            continue
    return skipped

def safe_copy(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists():
        shutil.copy2(src, dst)

def main():
    root = Path(".").resolve()

    done_root = root / DONE_OUTPUT_DIRNAME
    done_images = done_root / "IMAGES"
    done_errors = done_root / "ERRORS"

    finish_root = root / FINISH_OUTPUT_DIRNAME
    images_out = finish_root / "IMAGES"
    errors_out = finish_root / "ERRORS"
    images_out.mkdir(parents=True, exist_ok=True)
    errors_out.mkdir(parents=True, exist_ok=True)

    export_folders = find_export_folders(root)
    if not export_folders:
        raise SystemExit(f"No folders found containing '{EXPORT_FOLDER_SUBSTRING}' in: {root}")

    done_names = read_done_names(done_images)
    skipped_names = load_skipped_names(done_errors)  # optional but useful
    print(f"Already done: {len(done_names):,}")
    print(f"Already skipped (from previous errors): {len(skipped_names):,}")

    # 1) Read CSVs first to build remaining target set (fast)
    needed_date: dict[str, str] = {}
    needed_csv: dict[str, str] = {}

    csv_files = iter_csv_files(root)
    for csv_file in tqdm(csv_files, desc="Scanning CSVs for remaining items"):
        try:
            with open(csv_file, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    continue
                if not CSV_REQUIRED_COLUMNS.issubset(set(reader.fieldnames)):
                    continue

                for row in reader:
                    name = (row.get("imgName") or "").strip()
                    raw_date = (row.get("originalCreationDate") or "").strip()
                    if not name:
                        continue
                    if name in done_names or name in skipped_names:
                        continue
                    if name not in needed_date:
                        needed_date[name] = raw_date
                        needed_csv[name] = str(csv_file)
        except Exception:
            continue

    remaining = list(needed_date.keys())
    remaining_set = set(remaining)
    print(f"Remaining to process: {len(remaining):,}")
    if not remaining:
        print("Nothing left to do.")
        return

    # 2) Targeted disk scan: find only remaining files
    found_paths = defaultdict(list)
    for folder in tqdm(export_folders, desc="Scanning export folders for remaining files"):
        for f in folder.rglob("*"):
            if not f.is_file() or f.suffix.lower() == ".csv":
                continue
            if f.name in remaining_set:
                found_paths[f.name].append(f)

    # 3) Duplicates among remaining
    duplicates = {name: paths for name, paths in found_paths.items() if len(paths) > 1}
    with open(errors_out / "DUPLICATES.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for name, paths in duplicates.items():
            row = []
            for p in paths:
                row.extend([name, str(p)])
            w.writerow(row)

    # 4) Process remaining
    missing = []
    bad_date = []
    exiftool_failed = []
    processed = 0
    skipped_dup = 0

    et = ExifToolStayOpen()
    try:
        for name in tqdm(remaining, desc="Copying + stamping remaining"):
            paths = found_paths.get(name, [])
            if not paths:
                missing.append([name, needed_csv.get(name, "")])
                continue
            if name in duplicates:
                skipped_dup += 1
                continue

            src = paths[0]
            dst = images_out / name

            try:
                safe_copy(src, dst)
            except Exception:
                missing.append([name, needed_csv.get(name, "")])
                continue

            try:
                exif_date = parse_icloud_date(needed_date.get(name, ""))
            except Exception:
                bad_date.append([name, needed_date.get(name, ""), needed_csv.get(name, "")])
                continue

            if dst.suffix.lower() in VIDEO_EXTS:
                ok = et.run_args([
                    "-overwrite_original",
                    f"-CreateDate={exif_date}",
                    f"-MediaCreateDate={exif_date}",
                    f"-TrackCreateDate={exif_date}",
                    str(dst),
                ])
            else:
                ok = et.run_args([
                    "-overwrite_original",
                    f"-DateTimeOriginal={exif_date}",
                    f"-CreateDate={exif_date}",
                    str(dst),
                ])

            if not ok:
                exiftool_failed.append([name, exif_date, str(dst), needed_csv.get(name, "")])
                continue

            processed += 1
    finally:
        et.close()

    # 5) Write reports
    def write_csv(path: Path, header: list[str], rows: list[list[str]]):
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)

    write_csv(errors_out / "CANNOT_BE_FOUND.csv", ["imgName", "csvFile"], missing)
    write_csv(errors_out / "BAD_DATE.csv", ["imgName", "rawDate", "csvFile"], bad_date)
    write_csv(errors_out / "EXIFTOOL_FAILED.csv", ["imgName", "exifDate", "outputFile", "csvFile"], exiftool_failed)

    print("\nDONE (finish run)")
    print(f"Output: {finish_root}")
    print(f"Processed: {processed:,}")
    print(f"Skipped duplicates among remaining: {skipped_dup:,}")
    print(f"Missing: {len(missing):,}")
    print(f"Bad date: {len(bad_date):,}")
    print(f"Exiftool failed: {len(exiftool_failed):,}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)
