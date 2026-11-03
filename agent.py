#!/usr/bin/env python3
"""
TikTok Autonomous Browser Agent
Controls a browser instance to navigate TikTok, manage profiles, reposts, and content.
Includes visual grid photo-strip capture (screenshot -> scroll -> screenshot).
"""

import argparse
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent
PROFILE_DIR = BASE_DIR / "browser_profile"
CAPTURES_DIR = BASE_DIR / "captures"
SCREENSHOT_PATH = BASE_DIR / "current_page.png"

def accept_cookies_if_present(page):
    """Dismiss common TikTok cookie banners or guest modals."""
    selectors = [
        "button:has-text('Accept all')",
        "button:has-text('Alle akzeptieren')",
        "button:has-text('Allow all')",
        "button:has-text('Continue as guest')",
        "button:has-text('Als Gast fortfahren')",
        "[data-e2e='cookie-banner-accept']"
    ]
    for sel in selectors:
        try:
            elem = page.locator(sel).first
            if elem.is_visible(timeout=1200):
                print(f"[+] Cookie/Modal-Banner gefunden, klicke: {sel}")
                elem.click()
                time.sleep(1)
                break
        except Exception:
            pass

def main():
    parser = argparse.ArgumentParser(description="TikTok Autonomous Browser Agent")
    parser.add_argument("--profile", type=str, help="TikTok Benutzername (z. B. 'tiktok' oder '@tiktok')", default=None)
    parser.add_argument("--tab", type=str, choices=["Videos", "Reposts", "Favorites", "Liked", "Short dramas"], 
                        help="Tab auf dem Profil auswählen (z. B. Reposts)", default=None)
    parser.add_argument("--reposts", action="store_true", help="Schnellzugriff für den Reposts-Tab")
    parser.add_argument("--screens", type=int, default=1, help="Anzahl nacheinander gescrollter Screenshots der Profil-Grid (z. B. 5)")
    parser.add_argument("--scroll-step", type=int, default=650, help="Pixel pro Scrollschritt (Standard: 650px)")
    parser.add_argument("--headless", action="store_true", help="Im Hintergrund ohne Fenster starten")
    parser.add_argument("--keep-open", type=int, default=10, help="Sekunden, die der Browser offen bleibt (0 = bis Enter gedrückt wird)")
    args = parser.parse_args()

    if args.reposts:
        args.tab = "Reposts"

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    CAPTURES_DIR.mkdir(parents=True, exist_ok=True)

    print("==================================================")
    print("🚀 TikTok Autonomous Browser Agent")
    print(f"📁 Session/Profil: {PROFILE_DIR}")
    print(f"🖥️ Modus:          {'Headless (Hintergrund)' if args.headless else 'Sichtbares Fenster'}")
    print("==================================================")

    with sync_playwright() as p:
        context = p.firefox.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=args.headless,
            viewport={"width": 1280, "height": 900},
            locale="de-DE",
            args=["--no-sandbox"]
        )

        page = context.new_page()

        target_url = "https://www.tiktok.com"
        clean_user = "feed"
        if args.profile:
            clean_user = args.profile.lstrip("@")
            target_url = f"https://www.tiktok.com/@{clean_user}"

        print(f"[+] Navigiere zu: {target_url} ...")
        try:
            page.goto(target_url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(2500)
            print("[+] Seite geladen.")
        except Exception as e:
            print(f"[!] Ladefehler: {e}")

        accept_cookies_if_present(page)

        # Tab-Wechsel (z. B. Reposts / Erneute Veröffentlichungen)
        if args.tab:
            tab_aliases = {
                "Reposts": ["repost", "erneute veröffentlichung", "geteilt"],
                "Videos": ["video"],
                "Liked": ["like", "gelikt", "gefällt mir"],
                "Favorites": ["favorit"],
                "Short dramas": ["drama", "kurzdramen"]
            }
            candidates = tab_aliases.get(args.tab, [args.tab.lower()])
            print(f"[+] Suche nach Tab '{args.tab}' (Synonyme: {candidates})...")
            
            page.evaluate("window.scrollBy(0, 300)")
            page.wait_for_timeout(1000)

            clicked = False
            tab_elements = page.locator('[role="tab"]').all()
            for t in tab_elements:
                try:
                    text = t.inner_text().lower()
                    if any(c in text for c in candidates):
                        t.click()
                        print(f"[✓] Tab '{t.inner_text().strip()}' erfolgreich angeklickt!")
                        page.wait_for_timeout(2000)
                        clicked = True
                        break
                except Exception:
                    pass

            if not clicked:
                print(f"[-] Tab '{args.tab}' konnte nicht angeklickt werden.")

        # Einzelner Standard-Screenshot
        SCREENSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(SCREENSHOT_PATH))
        print(f"[✓] Haupt-Screenshot gesichert: {SCREENSHOT_PATH}")

        # Automatisches Scraping der Reposts in JSON, wenn Reposts gewählt wurden
        if args.tab == "Reposts" and args.profile:
            print(f"[*] Sammle Repost-Daten für @{clean_user}...")
            collected_items = {}
            for _ in range(5):  # 5 kurze Scrolls für ca. 30-60 Reposts
                cards = page.locator('div[data-e2e="user-post-item"], div[class*="DivItemContainerV2"], div[data-e2e="user-repost-item"]').all()
                if not cards:
                    cards = page.locator('a[href*="/video/"]').all()

                for card in cards:
                    link_elem = card if card.evaluate("node => node.tagName.toLowerCase() === 'a'") else card.locator('a[href*="/video/"]').first
                    href = link_elem.get_attribute("href") if link_elem.count() > 0 else None
                    if not href or "/video/" not in href:
                        continue

                    video_id = href.split("/video/")[1].split("?")[0] if "/video/" in href else href
                    if video_id in collected_items:
                        continue

                    img = card.locator("img").first
                    alt = img.get_attribute("alt") if img.count() > 0 else ""
                    views_elem = card.locator('[data-e2e="video-views"], strong').first
                    views = views_elem.inner_text() if views_elem.count() > 0 else ""
                    card_text = card.inner_text().replace("\n", " ").strip()

                    collected_items[video_id] = {
                        "order_index": len(collected_items) + 1,
                        "video_id": video_id,
                        "url": href,
                        "caption_alt": alt,
                        "views": views,
                        "card_text": card_text
                    }

                page.evaluate("window.scrollBy(0, 800)")
                page.wait_for_timeout(1000)

            items_list = list(collected_items.values())
            json_out = BASE_DIR / f"{clean_user}_reposts.json"
            with open(json_out, "w", encoding="utf-8") as f:
                import json
                json.dump(items_list, f, indent=2, ensure_ascii=False)
            print(f"[✓] {len(items_list)} Reposts gespeichert in: {json_out.name}")

        # Multi-Screen Grid Capture: Screenshot -> Scroll -> Screenshot ...
        if args.screens > 1:
            user_capture_dir = CAPTURES_DIR / clean_user
            user_capture_dir.mkdir(parents=True, exist_ok=True)
            print(f"\n📸 Starte Grid-Fotostrecke ({args.screens} Screenshots)...")
            
            # Zunächst zum Grid-Anfang scrollen (Profil-Header überspringen)
            page.evaluate("window.scrollTo(0, 350)")
            page.wait_for_timeout(1500)

            captured_files = []
            for i in range(1, args.screens + 1):
                screen_file = user_capture_dir / f"grid_{i:02d}.png"
                # Sicherstellen, dass neue Bilder im Viewport geladen sind
                page.wait_for_timeout(1200)
                page.screenshot(path=str(screen_file))
                captured_files.append(screen_file)
                print(f"  [✓ Screen {i:02d}/{args.screens:02d}] Gespeichert: {screen_file.name}")
                
                # Weiterscrollen für den nächsten Bildausschnitt
                if i < args.screens:
                    page.evaluate(f"window.scrollBy(0, {args.scroll_step})")

            print(f"\n[✓] Fotostrecke komplett! {len(captured_files)} Screenshots in: {user_capture_dir}")

        print(f"[✓] Aktueller Titel: {page.title()}")
        print(f"[✓] Aktuelle URL:   {page.url}")

        if args.keep_open == 0:
            print("\n[i] Browser bleibt geöffnet. Drücke [ENTER] im Terminal zum Schließen...")
            input()
        elif args.keep_open > 0:
            print(f"\n[i] Browser bleibt noch {args.keep_open} Sekunden geöffnet...")
            time.sleep(args.keep_open)

        context.close()
        print("[+] Fertig.")

if __name__ == "__main__":
    main()
