#!/usr/bin/env python3
"""
Mood & Sentiment Timeline Analysis for TikTok Reposts.
Processes any user's repost JSON and analyzes emotional transitions over time.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from collections import Counter

BASE_DIR = Path(__file__).resolve().parent

CATEGORIES = {
    "action_adrenalin": [
        "bikelife", "supermoto", "dirtbike", "motorrad", "yz125", "yz450f", "2stroke",
        "wrc", "rally", "motorsport", "racing", "e36", "bmw", "tuning", "drift",
        "fullsend", "full pin", "speed", "simson", "starkvarg"
    ],
    "party_euphorie": [
        "party", "saufen", "wochenende", "bier", "beer", "drunk", "feiern", "club",
        "banger", "crazy", "halloween", "dance", "alkohol", "vibes", "feierabend"
    ],
    "liebe_freundschaft": [
        "friends", "freunde", "sister", "liebe", "love", "süss", "spitznamen", "cute",
        "twin", "bestie", "herz", "forever", "relationship", "pärchen", "family"
    ],
    "melancholie_heartbreak": [
        "brokenheart", "lonely", "einsam", "traurig", "sad", "miss", "vermissen",
        "herzschmerz", "schmerz", "cry", "weinen", "alone", "tränen", "overthinking",
        "hurt", "why", "enttäuscht", "depressed", "depri"
    ],
    "frust_stress_alltag": [
        "schule", "school", "exams", "klausuren", "arbeit", "berufsschule", "stress",
        "cortisol", "müde", "kein bock", "montag", "nervt", "hass", "ausbildung", "work"
    ],
    "humor_relatable": [
        "relateable", "relatable", "fy", "viral", "fyp", "real", "eif", "fühlen",
        "wer kennts", "meme", "peak", "lashes", "dorf", "landwirtschaft"
    ]
}

def classify_text(text):
    text_lower = text.lower()
    scores = {cat: 0 for cat in CATEGORIES}
    for cat, keywords in CATEGORIES.items():
        for kw in keywords:
            if re.search(r'\b' + re.escape(kw) + r'\b', text_lower) or kw in text_lower:
                scores[cat] += 1
    max_cat = max(scores, key=scores.get)
    if scores[max_cat] == 0:
        return "neutral_alltag", scores
    return max_cat, scores

def resolve_input_file(target):
    p = Path(target)
    if p.exists() and p.is_file():
        return p
    clean = target.lstrip("@").lower()
    prefix = clean.split(".")[0]
    candidates = [
        BASE_DIR / f"{clean}_reposts.json",
        BASE_DIR / f"{clean}_200_reposts.json",
        BASE_DIR / f"{clean}_100_reposts.json",
        BASE_DIR / f"{prefix}_reposts.json"
    ]
    for c in candidates:
        if c.exists():
            return c
    for f in BASE_DIR.glob(f"*{prefix}*.json"):
        if "repost" in f.name:
            return f
    return None

def analyze(target_user_or_file):
    input_file = resolve_input_file(target_user_or_file)
    if not input_file:
        print(f"[!] Fehler: Keine Repost-Daten für '{target_user_or_file}' gefunden.")
        print("    Führe zuerst 'tiktok-bot --profile <user> --reposts' aus.")
        sys.exit(1)

    with open(input_file, "r", encoding="utf-8") as f:
        reposts = json.load(f)

    total = len(reposts)
    print(f"[*] Analysiere {total} Reposts aus {input_file.name}...")

    chronological = list(reversed(reposts))
    analyzed_items = []
    category_counts = Counter()

    for idx, item in enumerate(chronological):
        text_to_analyze = f"{item.get('caption_alt', '')} {item.get('card_text', '')}"
        dominant, scores = classify_text(text_to_analyze)
        category_counts[dominant] += 1
        analyzed_items.append({
            "chrono_step": idx + 1,
            "original_order_index": item.get("order_index", idx + 1),
            "url": item.get("url", ""),
            "views": item.get("views", ""),
            "text": text_to_analyze,
            "dominant_mood": dominant,
            "scores": scores
        })

    num_phases = 4 if total >= 40 else 2
    chunk_size = max(len(analyzed_items) // num_phases, 1)
    phases = []

    for p in range(num_phases):
        start = p * chunk_size
        end = (p + 1) * chunk_size if p < num_phases - 1 else len(analyzed_items)
        phase_items = analyzed_items[start:end]
        phase_counts = Counter([item["dominant_mood"] for item in phase_items])
        phases.append({
            "phase": p + 1,
            "range": f"Post {start + 1} bis {end} (Chronologisch von alt nach neu)",
            "total_posts": len(phase_items),
            "distribution": dict(phase_counts),
            "top_mood": phase_counts.most_common(1)[0] if phase_counts else ("none", 0)
        })

    report = {
        "source_file": input_file.name,
        "total_analyzed": total,
        "overall_distribution": dict(category_counts),
        "phases": phases,
        "items": analyzed_items
    }

    report_file = BASE_DIR / f"mood_report_{input_file.stem}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"[✓] Analyse abgeschlossen! Bericht gespeichert in: {report_file.name}")
    print("\n--- Gesamtverteilung ---")
    for cat, count in category_counts.most_common():
        pct = (count / total) * 100
        print(f"  {cat:25s}: {count:3d} ({pct:5.1f}%)")

def main():
    parser = argparse.ArgumentParser(description="Timeline Sentiment & Mood Analysis for TikTok Reposts")
    parser.add_argument("target", help="Benutzername oder JSON-Datei zur Analyse")
    args = parser.parse_args()
    analyze(args.target)

if __name__ == "__main__":
    main()
