#!/usr/bin/env python3
"""
TikTok Profile Compatibility & Matcher Agent (`tiktok-match`)
Compares two TikTok profiles based on their reposts and visual metadata.

Supports three operational modes:
1. 🧠 LLM Mode (Gemini API): Deep psychological, subtext, and romantic compatibility analysis.
2. 🤖 Agent Mode: Generates structured artifacts for AI agents (Antigravity, Cursor, etc.) to evaluate.
3. 📊 Heuristic Fallback Mode: Statistical and keyword-based overlap without any API key.
"""

import argparse
import json
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

CATEGORIES = {
    "bikelife_tuning": ["simson", "supermoto", "beta", "ktm", "vesc", "escooter", "g4", "tuning", "2stroke", "dirtbike", "starkvarg", "schwalbe"],
    "romantik_deeptalk": ["love", "eyes", "eyecontact", "spazieren", "bank", "her", "liebe", "deeptalk", "anruf", "spitznamen", "beziehung", "single"],
    "party_wochenende": ["party", "freitag", "wochenende", "bier", "beer", "saufen", "halloween", "alkohol", "drink", "banger"],
    "schule_stress": ["schule", "school", "hausaufgaben", "unterricht", "exams", "berufsschule", "10. klasse", "stress", "müde"],
    "relatable_memes": ["relatable", "relateable", "bro", "fy", "viral", "fyp", "dumm", "nachdenken", "overthinking"]
}

def get_api_key(explicit_key=None):
    """Retrieve Gemini API key from args, env, or .env file."""
    if explicit_key:
        return explicit_key
    if "GEMINI_API_KEY" in os.environ:
        return os.environ["GEMINI_API_KEY"]
    
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("GEMINI_API_KEY="):
                    return line.strip().split("=", 1)[1].strip("\"' ")
    return None

def load_or_fetch(user):
    import subprocess
    clean_user = user.lstrip("@").lower()
    prefix = clean_user.split(".")[0]
    
    candidates = [
        BASE_DIR / f"{clean_user}_200_reposts.json",
        BASE_DIR / f"{clean_user}_100_reposts.json",
        BASE_DIR / f"{clean_user}_reposts.json",
        BASE_DIR / f"{prefix}_200_reposts.json",
        BASE_DIR / f"{prefix}_100_reposts.json",
        BASE_DIR / f"{prefix}_reposts.json"
    ]
    for p in candidates:
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f), p

    for f in BASE_DIR.glob(f"*{prefix}*.json"):
        if "repost" in f.name:
            with open(f, "r", encoding="utf-8") as fl:
                return json.load(fl), f

    print(f"[*] Keine Daten für @{user} gefunden. Starte automatische Erfassung im Hintergrund...")
    agent_script = BASE_DIR / "agent.py"
    try:
        subprocess.run(
            [sys.executable, str(agent_script), "--profile", user, "--reposts", "--headless", "--keep-open", "1"],
            check=True
        )
        json_out = BASE_DIR / f"{clean_user}_reposts.json"
        if json_out.exists():
            with open(json_out, "r", encoding="utf-8") as f:
                return json.load(f), json_out
    except Exception as e:
        print(f"[!] Fehler beim automatischen Abrufen für @{user}: {e}")

    return None, None

def analyze_profile_categories(items):
    counts = {cat: 0 for cat in CATEGORIES}
    total = len(items)
    for it in items:
        txt = (it.get("caption_alt", "") + " " + it.get("card_text", "")).lower()
        for cat, kws in CATEGORIES.items():
            if any(k in txt for k in kws):
                counts[cat] += 1
    return counts, total

def run_ai_gemini_match(u1, items1, u2, items2, api_key):
    """Run an advanced psychological compatibility analysis using Gemini API."""
    try:
        from google import genai
    except ImportError:
        print("[!] Paket 'google-genai' nicht gefunden. Führe 'pip install google-genai' aus.")
        return None

    print("\n🧠 Starte KI-Analyse mit der Gemini API (Deep Psychological Evaluation)...")
    try:
        client = genai.Client(api_key=api_key)
        
        # Prepare concise sample payload for the prompt
        sample_posts1 = [f"- {it.get('caption_alt', '')[:100]}" for it in items1[:40] if it.get('caption_alt')]
        sample_posts2 = [f"- {it.get('caption_alt', '')[:100]}" for it in items2[:40] if it.get('caption_alt')]

        prompt = f"""Du bist ein empathischer, psychologisch scharfsinniger Beziehungs- und Social-Media-Experte.
Analysiere die TikTok-Reposts zweier Personen und erstelle eine tiefgründige, ehrliche Kompatibilitätsanalyse.

PROFIL 1: @{u1} ({len(items1)} Reposts analysiert)
Auszug der Reposts:
{chr(10).join(sample_posts1)}

PROFIL 2: @{u2} ({len(items2)} Reposts analysiert)
Auszug der Reposts:
{chr(10).join(sample_posts2)}

AUFGABE:
1. Psychologisches Kurzprofil beider Personen (Werte, Sehnsüchte, Schutzmauern).
2. Gemeinsame Nischen & Verborgene Parallelen (auch wenn unterschiedliche Worte verwendet werden!).
3. Mögliche Reibungspunkte (z. B. Kommunikationsstile, Rückzug, Ghosting/Auf-Gelesen-Lassen).
4. Kompatibilitäts-Score (in Prozent 0-100%).
5. 3 konkrete, unverkrampfte Konversations- und Date-Tipps für ein Treffen der beiden.

Formatiere die Antwort übersichtlich in GitHub-Markdown."""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text
    except Exception as e:
        print(f"[!] Fehler bei der Gemini-API-Anfrage: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="TikTok Profile Matcher (AI-Powered & Heuristic)")
    parser.add_argument("user1", help="Erster Benutzername (z. B. user_a)")
    parser.add_argument("user2", help="Zweiter Benutzername (z. B. user_b)")
    parser.add_argument("--api-key", type=str, default=None, help="Google Gemini API Key für direkte KI-Bewertung")
    parser.add_argument("--no-ai", action="store_true", help="Erzwinge reine statistische/heuristische Auswertung")
    args = parser.parse_args()

    u1 = args.user1.lstrip("@")
    u2 = args.user2.lstrip("@")

    items1, file1 = load_or_fetch(u1)
    items2, file2 = load_or_fetch(u2)

    if not items1 or not items2:
        print(f"[!] Fehler: Daten für einen der Nutzer fehlen ({u1}: {bool(items1)}, {u2}: {bool(items2)}).")
        print("    Führe zuerst 'tiktok-bot --profile <user> --reposts' aus, um Daten zu erfassen.")
        sys.exit(1)

    print("==================================================")
    print(f"💘 TikTok Compatibility Matcher: @{u1} ❤️ @{u2}")
    print("==================================================")
    print(f"📁 Datengrundlage: {len(items1)} Posts (@{u1}) vs. {len(items2)} Posts (@{u2})")

    # 1. Identische Reposts ermitteln
    dict1 = {it["video_id"]: it for it in items1 if "video_id" in it}
    dict2 = {it["video_id"]: it for it in items2 if "video_id" in it}
    common_ids = set(dict1.keys()) & set(dict2.keys())

    print(f"\n🔥 Exakt identische Reposts: {len(common_ids)}")
    for vid in list(common_ids)[:5]:
        caption = dict1[vid].get("caption_alt", "")[:90]
        print(f"   • Video {vid}: {caption}")

    # 2. Prüfen auf KI-Auswertung via Gemini
    api_key = get_api_key(args.api_key)
    if api_key and not args.no_ai:
        ai_result = run_ai_gemini_match(u1, items1, u2, items2, api_key)
        if ai_result:
            print("\n" + "=" * 50)
            print("✨ KI-ANALYSE-ERGEBNIS (GEMINI)")
            print("=" * 50)
            print(ai_result)
            return

    # 3. Statistische / Heuristische Auswertung (Fallback)
    counts1, tot1 = analyze_profile_categories(items1)
    counts2, tot2 = analyze_profile_categories(items2)

    category_scores = {}
    print("\n📊 Themen-Übereinstimmung (Heuristik):")
    for cat in CATEGORIES:
        pct1 = (counts1[cat] / tot1) * 100 if tot1 else 0
        pct2 = (counts2[cat] / tot2) * 100 if tot2 else 0
        overlap = min(pct1, pct2) / max(pct1, pct2) * 100 if max(pct1, pct2) > 0 else 50
        category_scores[cat] = overlap
        print(f"   {cat:22s}: @{u1}: {pct1:4.1f}% | @{u2}: {pct2:4.1f}% => Match: {overlap:5.1f}%")

    # Dynamische komplementäre Treffer
    def has_kws(items, kws):
        for it in items:
            t = (it.get("caption_alt", "") + " " + it.get("card_text", "")).lower()
            if any(k in t for k in kws):
                return True
        return False

    complementary_hits = []
    if has_kws(items1, ["spazieren", "spaziergang"]) and has_kws(items2, ["spazieren", "spaziergang"]):
        complementary_hits.append(("Nachts Spazieren gehen", "Beide teilten den Wunsch nach stundenlangen Nachtspaziergängen."))
    if has_kws(items1, ["spitzname", "nickname"]) and has_kws(items2, ["spitzname", "nickname"]):
        complementary_hits.append(("Spitznamen statt Name", "Beide feiern es, mit Kosenamen/Spitznamen angesprochen zu werden."))
    if has_kws(items1, ["bier", "beer", "heineken"]) and has_kws(items2, ["bier", "beer", "heineken"]):
        complementary_hits.append(("Bier & Feierabend", "Beide haben denselben Wochenend- und Bier-Humor geteilt."))
    if has_kws(items1, ["unter uns", "vertrauen", "loyal"]) and has_kws(items2, ["unter uns", "vertrauen", "loyal"]):
        complementary_hits.append(("Vertrauen & Loyalität", "Beide legten großen Wert auf Verschwiegenheit ('...bleibt unter uns')."))
    if has_kws(items1, ["simson", "supermoto", "vesc", "2stroke"]) and has_kws(items2, ["simson", "supermoto", "vesc", "2stroke"]):
        complementary_hits.append(("Zweitakt, Moped & Bikelife", "Beide teilen die Leidenschaft für Zweitakter/Mopeds/Bikes."))

    if complementary_hits:
        print("\n✨ Komplementäre 'Seelenverwandtschafts'-Muster:")
        for title, desc in complementary_hits:
            print(f"   ✓ {title}: {desc}")

    base_score = sum(category_scores.values()) / len(category_scores)
    bonus_common = min(len(common_ids) * 4, 20)
    bonus_complementary = len(complementary_hits) * 3
    final_score = min(int(base_score + bonus_common + bonus_complementary), 99)

    print("\n" + "=" * 50)
    print(f"💖 GESAMT-KOMPATIBILITÄT: {final_score}% MATCH!")
    print("=" * 50)
    print("💡 HINWEIS: Setze die Umgebungsvariable 'GEMINI_API_KEY' oder nutze einen")
    print("            KI-Agenten (wie Antigravity/Cursor), um eine vollwertige")
    print("            psychologische Tiefenanalyse mit Sprachmodell auszulösen.")
    print("=" * 50)

if __name__ == "__main__":
    main()
