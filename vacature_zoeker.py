"""
Wekelijkse vacaturezoeker voor jonge asielzoekers in Deventer.

Dit script scrapet GEEN externe vacaturesites (Indeed, Nationale
Vacaturebank, LinkedIn, e.d.) — dat is meestal in strijd met hun
gebruiksvoorwaarden en te broos om betrouwbaar wekelijks te draaien.

In plaats daarvan werkt het met twee door de begeleider(s) zelf
bijgehouden bronnen:

  - data/vacatures_bron.csv : de "pool" van kansrijke vacatures die je
    zelf vindt (via vacaturesites, mond-tot-mondreclame, netwerk) en
    hier handmatig aan toevoegt.
  - bedrijven_lijst.txt      : lokale vertrouwde bedrijven die voorrang
    krijgen bij de wekelijkse selectie.

Het script kiest hieruit wekelijks de top 3 meest urgente, ongeschoolde
vacatures/bijbanen, geeft per vacature een overtuigende reden en een
belscript, en zorgt dat dezelfde vacature niet elke week opnieuw
bovenaan staat.

BELANGRIJK — juridische context:
Dit gaat om jonge ASIELZOEKERS (nog in de asielprocedure), geen
statushouders. Zij mogen alleen werken met een geldig W-document, en
de werkgever moet vooraf een tewerkstellingsvergunning (TWV) aanvragen
bij UWV (maximaal 24 van de 52 weken per jaar). Voor minderjarigen
gelden aanvullende, strengere regels. Dit script geeft geen juridisch
advies — controleer de actuele regels altijd bij UWV / VluchtelingenWerk
Nederland / COA voordat je een jongere naar een werkgever stuurt.
"""

import argparse
import csv
import json
from datetime import date, datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
BEDRIJVEN_LIJST_PATH = BASE_DIR / "bedrijven_lijst.txt"
VACATURES_BRON_PATH = BASE_DIR / "data" / "vacatures_bron.csv"
STATE_PATH = BASE_DIR / "data" / "laatst_getoond.json"
OUTPUT_DIR = BASE_DIR / "output"
ARCHIEF_DIR = OUTPUT_DIR / "archief"

REGIO_TREFWOORD = "deventer"
URGENTIE_TREFWOORDEN = ["spoed", "dringend", "per direct", "nu", "meteen", "acuut", "tekort"]
HERHAAL_WEKEN = 3  # zelfde vacature niet vaker dan 1x per 3 weken opnieuw tonen


def laad_vertrouwde_bedrijven():
    vertrouwd = set()
    if not BEDRIJVEN_LIJST_PATH.exists():
        return vertrouwd
    for regel in BEDRIJVEN_LIJST_PATH.read_text(encoding="utf-8").splitlines():
        regel = regel.strip()
        if not regel or regel.startswith("#"):
            continue
        naam = regel.split("|")[0].strip()
        if naam:
            vertrouwd.add(naam.lower())
    return vertrouwd


def laad_vacatures():
    if not VACATURES_BRON_PATH.exists():
        return []
    with VACATURES_BRON_PATH.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def laad_state():
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {}


def bewaar_state(state):
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def is_actief_en_geschikt(vacature):
    actief = vacature.get("actief", "ja").strip().lower()
    if actief not in ("ja", "yes", "y", ""):
        return False
    regio = vacature.get("regio", "").strip().lower()
    if REGIO_TREFWOORD not in regio:
        return False
    return True


def bereken_score(vacature, vertrouwde_bedrijven, state, vandaag):
    score = 0

    telefoon = vacature.get("telefoonnummer", "").strip()
    if telefoon.replace(" ", "").replace("-", "").startswith("06"):
        score += 50  # direct 06-nummer = kunnen meteen bellen ipv formulier

    bedrijf = vacature.get("bedrijf", "").strip()
    if bedrijf.lower() in vertrouwde_bedrijven:
        score += 30  # bekend en vertrouwd lokaal bedrijf

    if vacature.get("ongeschoold", "").strip().lower() in ("ja", "yes", "y"):
        score += 20

    reden = vacature.get("reden_urgentie", "").lower()
    if any(woord in reden for woord in URGENTIE_TREFWOORDEN):
        score += 15

    datum_str = vacature.get("datum_gevonden", "").strip()
    if datum_str:
        try:
            gevonden = datetime.strptime(datum_str, "%Y-%m-%d").date()
            leeftijd_dagen = (vandaag - gevonden).days
            if leeftijd_dagen <= 7:
                score += 10
            elif leeftijd_dagen <= 14:
                score += 5
        except ValueError:
            pass

    sleutel = f"{bedrijf}|{vacature.get('functie', '')}"
    laatst_getoond_str = state.get(sleutel)
    if laatst_getoond_str:
        try:
            laatst = datetime.strptime(laatst_getoond_str, "%Y-%m-%d").date()
            if (vandaag - laatst).days < HERHAAL_WEKEN * 7:
                score -= 1000  # recent al getoond -> naar achteren
        except ValueError:
            pass

    return score


def kies_top_vacatures(vacatures, vertrouwde_bedrijven, state, vandaag, aantal=3):
    geschikt = [v for v in vacatures if is_actief_en_geschikt(v)]
    gescoord = [(bereken_score(v, vertrouwde_bedrijven, state, vandaag), v) for v in geschikt]
    gescoord.sort(key=lambda item: item[0], reverse=True)
    return [v for _, v in gescoord[:aantal]]


def genereer_telefoonscript(vacature):
    functie = vacature.get("functie", "de functie").lower()
    return (
        "\"Hallo, u spreekt met [naam begeleider] van [organisatie] in Deventer. "
        f"Ik zag dat jullie op zoek zijn naar iemand voor {functie}. "
        "Ik begeleid een gemotiveerde jongere die snel wil starten en graag langs wil komen "
        "om kennis te maken. Hij/zij zit in de asielprocedure en heeft een geldig W-document; "
        "voor de start regelen we samen met u de werkvergunning (TWV) via UWV — dat duurt "
        "meestal enkele weken, dus hoe eerder we de aanvraag starten, hoe beter. "
        "Zou ik hem/haar vandaag of morgen mogen voorstellen?\""
    )


def maak_markdown_tabel(top_vacatures, vandaag):
    regels = []
    regels.append(f"# Vacatures van de week — {vandaag.isoformat()}")
    regels.append("")
    regels.append(
        "**Juridische let-op:** dit betreft jonge **asielzoekers** (nog in de "
        "asielprocedure), geen statushouders. Werken mag alleen met een geldig "
        "**W-document**, en de werkgever moet vooraf een "
        "**tewerkstellingsvergunning (TWV)** aanvragen bij UWV (max. 24 van de 52 "
        "weken per jaar). Reken op enkele weken doorlooptijd — begin de aanvraag "
        "dus zo snel mogelijk. Bij minderjarigen gelden aanvullende, strengere "
        "regels: controleer dit altijd eerst bij UWV / VluchtelingenWerk / COA."
    )
    regels.append("")

    if not top_vacatures:
        regels.append(
            "_Geen geschikte vacatures gevonden in data/vacatures_bron.csv voor regio "
            "Deventer. Vul dit bestand aan met actuele vacatures._"
        )
        return "\n".join(regels)

    regels.append("| Functie | Bedrijf | 06-nummer | Vacaturelink | Actie |")
    regels.append("|---|---|---|---|---|")
    for v in top_vacatures:
        functie = v.get("functie", "")
        bedrijf = v.get("bedrijf", "")
        telefoon = v.get("telefoonnummer", "").strip()
        link = v.get("vacature_link", "").strip()
        link_md = f"[link]({link})" if link else "-"
        actie = "Bel direct" if telefoon.replace(" ", "").replace("-", "").startswith("06") else "Vul formulier in / mail"
        regels.append(f"| {functie} | {bedrijf} | {telefoon or '-'} | {link_md} | {actie} |")
    regels.append("")

    for i, v in enumerate(top_vacatures, start=1):
        regels.append(f"## {i}. {v.get('functie', '')} bij {v.get('bedrijf', '')}")
        regels.append("")
        regels.append(f"**Waarom nu:** {v.get('reden_urgentie') or 'Geen reden opgegeven.'}")
        regels.append("")
        regels.append(f"**Contactpersoon:** {v.get('contactpersoon') or 'onbekend'}")
        regels.append("")
        regels.append("**Wat te zeggen aan de telefoon:**")
        regels.append("")
        regels.append(genereer_telefoonscript(v))
        regels.append("")

    return "\n".join(regels)


def update_state(state, top_vacatures, vandaag):
    for v in top_vacatures:
        sleutel = f"{v.get('bedrijf', '')}|{v.get('functie', '')}"
        state[sleutel] = vandaag.isoformat()
    return state


def main():
    parser = argparse.ArgumentParser(description="Wekelijkse vacaturezoeker voor jonge asielzoekers in Deventer")
    parser.add_argument("--aantal", type=int, default=3, help="Aantal vacatures om te selecteren (standaard 3)")
    parser.add_argument("--dry-run", action="store_true", help="Schrijf geen output/state weg, toon alleen resultaat")
    args = parser.parse_args()

    vandaag = date.today()
    vertrouwde_bedrijven = laad_vertrouwde_bedrijven()
    vacatures = laad_vacatures()
    state = laad_state()

    if not vacatures:
        print(
            "Geen vacatures gevonden in data/vacatures_bron.csv. "
            "Vul dit bestand eerst met (echte) vacatures voordat je het script draait."
        )
        return

    top_vacatures = kies_top_vacatures(vacatures, vertrouwde_bedrijven, state, vandaag, args.aantal)
    markdown = maak_markdown_tabel(top_vacatures, vandaag)

    if args.dry_run:
        print(markdown)
        return

    OUTPUT_DIR.mkdir(exist_ok=True)
    ARCHIEF_DIR.mkdir(exist_ok=True, parents=True)
    (OUTPUT_DIR / "vacatures_deze_week.md").write_text(markdown, encoding="utf-8")
    (ARCHIEF_DIR / f"vacatures_{vandaag.isoformat()}.md").write_text(markdown, encoding="utf-8")

    state = update_state(state, top_vacatures, vandaag)
    bewaar_state(state)

    print(markdown)


if __name__ == "__main__":
    main()
