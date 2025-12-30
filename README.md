# iCloud Photos Export – Date Fixer

This tool fixes incorrect or missing "Date Taken" metadata in Apple iCloud photo exports by restoring the original capture timestamps from Apple’s metadata files.

It is designed for large libraries and safely processes tens of thousands of photos.

---

## What This Tool Does

- Reads Apple iCloud metadata (CSV / JSON)
- Copies photos and videos into a clean output folder
- Writes correct EXIF timestamps
- Preserves original files (non-destructive)
- Handles large libraries efficiently

---

## Folder Structure

```
iCloud Photos 1 of 13/
iCloud Photos 2 of 13/
...
```

Output:
```
NEW_IMAGES_SORTED/
  IMAGES/
  ERRORS/
```

---

## Requirements

- Windows 10 or 11  
- Python 3.10 or newer  
- ExifTool (installed and added to PATH)

---

## Installation

1. Install Python from https://www.python.org  
2. Install ExifTool from https://exiftool.org  
3. Add ExifTool to your system PATH  

Verify:
```
exiftool -ver
```

---

## Usage

Run the script from the directory containing your iCloud folders:

```
python sort_icloud_photos.py
```

To resume a partial run:

```
python finish_icloud_photos.py
```

---

## Output

```
NEW_IMAGES_SORTED/
  IMAGES/
  ERRORS/
```

---

## License

MIT License
