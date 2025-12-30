# iCloud Photos Export – Date Fixer

Apple’s iCloud photo exports often lose or corrupt the original “Date Taken” metadata, causing photos to appear in the wrong order or wrong year when imported into other apps.

This tool fixes that problem by reading Apple’s own metadata files and restoring the correct capture timestamps directly into each photo and video. It safely rebuilds accurate EXIF data so your library sorts correctly in any photo manager, including Immich, Lightroom, and Photos.

Designed for large libraries, it processes tens of thousands of files reliably while keeping the original media untouched.

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

4. Clone the repository
5. Install dependencies:

   pip install -r requirements.txt


---

## Usage

Run the script from the directory containing your iCloud folders:

```
python sort_icloud_photos.py
```

To resume a partial run in cases of powercuts or other failures:

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
