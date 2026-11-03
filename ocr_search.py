#!/usr/bin/env python3
"""
TikTok Screenshot OCR & Text Search Engine (`tiktok-search`)
Scans all grid screenshots with Tesseract OCR (German + English),
indexes all visible text overlays, and enables instant keyword search.
"""

import argparse
import json
import sys
from pathlib import Path
from PIL import Image
import pytesseract

BASE_DIR = Path(__file__).resolve().parent
CAPTURES_DIR = BASE_DIR / "captures"
INDEX_FILE = BASE_DIR / "ocr_index.json"

def build_index(force=False):
    index = {}
    if INDEX_FILE.exists() and not force:
        try:
            with open(INDEX_FILE, "r", encoding="utf-8") as f:
                index = json.load(f)
        except Exception:
            index = {}

    all_images = list(CAPTURES_DIR.glob("**/*.png"))
    if not all_images:
        print("[!] Keine Screenshots in 'captures/' gefunden. Führe erst 'tiktok-bot --screens' aus.")
        return index

    updated = False
    print(f"[*] Überprüfe OCR-Index für {len(all_images)} Screenshots...")
    for img_path in sorted(all_images):
        rel_key = str(img_path.relative_to(CAPTURES_DIR))
        mtime = img_path.stat().st_mtime

        if rel_key in index and index[rel_key].get("mtime") == mtime and not force:
            continue

        print(f"  [+] OCR scanne: {rel_key} ...")
        try:
            img = Image.open(img_path)
            raw_text = pytesseract.image_to_string(img, lang="deu+eng")
            lines = [l.strip() for l in raw_text.splitlines() if len(l.strip()) > 3]
            index[rel_key] = {
                "user": img_path.parent.name,
                "file": img_path.name,
                "path": str(img_path),
                "mtime": mtime,
                "lines": lines,
                "full_text": "\n".join(lines)
            }
            updated = True
        except Exception as e:
            print(f"  [!] Fehler bei {rel_key}: {e}")

    if updated or not INDEX_FILE.exists():
        with open(INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
        print(f"[✓] OCR-Index aktualisiert ({len(index)} Bilder indexiert).")

    return index

def search(query, user_filter=None, reindex=False):
    index = build_index(force=reindex)
    q_lower = query.lower()

    matches = []
    for rel_key, data in index.items():
        if user_filter and user_filter.lower() not in data["user"].lower():
            continue

        hit_lines = [line for line in data["lines"] if q_lower in line.lower()]
        if hit_lines:
            matches.append((data, hit_lines))

    print("\n" + "=" * 60)
    print(f"🔍 OCR-Suchergebnisse für: '{query}'" + (f" (User: {user_filter})" if user_filter else ""))
    print("=" * 60)

    if not matches:
        print(f"[-] Keine Texttreffer für '{query}' in den Screenshots gefunden.")
        return

    print(f"[✓] {len(matches)} Screenshots mit Treffern gefunden:\n")
    for data, lines in matches:
        print(f"📸 {data['user']} / {data['file']}")
        print(f"   Pfad: file://{data['path']}")
        print("   Gefundener Text im Bild:")
        for l in lines:
            # Highlight query in terminal
            print(f"     👉 \"{l}\"")
        print()

def main():
    parser = argparse.ArgumentParser(description="TikTok Screenshot OCR Search Engine")
    parser.add_argument("query", nargs="?", default=None, help="Suchbegriff (z. B. 'spazieren', 'bier', 'wochenende')")
    parser.add_argument("--user", type=str, default=None, help="Nur Screenshots eines bestimmten Nutzers durchsuchen")
    parser.add_argument("--reindex", action="store_true", help="Index neu aufbauen")
    args = parser.parse_args()

    if not args.query and not args.reindex:
        parser.print_help()
        sys.exit(0)

    if args.reindex and not args.query:
        build_index(force=True)
        return

    search(args.query, user_filter=args.user, reindex=args.reindex)

if __name__ == "__main__":
    main()
