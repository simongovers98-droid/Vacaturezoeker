# Vacaturezoeker Deventer — voor begeleiders van jonge asielzoekers

Een klein, geautomatiseerd systeem dat wekelijks de **top 3 meest urgente
vacatures** (ongeschoold werk / bijbanen) in regio Deventer selecteert,
prioriteit geeft aan vacatures met een direct 06-nummer, en per vacature
een overtuigende reden + belscript genereert.

## Belangrijk: asielzoekers, geen statushouders

Dit systeem is bedoeld voor jonge **asielzoekers** die nog in de
asielprocedure zitten — niet voor statushouders. Dat maakt praktisch
verschil:

- Werken mag alleen als de jongere een geldig **W-document** heeft (dat
  krijgt iemand pas na een bepaalde periode in de procedure).
- De **werkgever** moet vóór de startdatum een
  **tewerkstellingsvergunning (TWV)** aanvragen bij UWV. Reken op enkele
  weken doorlooptijd — dus hoe eerder de aanvraag start, hoe beter.
- Er geldt een **24-weken-eis**: maximaal 24 van de 52 weken per jaar mag
  gewerkt worden.
- Voor **minderjarigen** gelden aanvullende, strengere regels (vaak geen
  regulier werk, wel bijvoorbeeld stages binnen onderwijs).

Dit script geeft geen juridisch advies. Check de actuele regels altijd bij
UWV, VluchtelingenWerk Nederland of COA voordat je een jongere naar een
werkgever stuurt. Het gegenereerde belscript benoemt dit bewust meteen aan
de telefoon, zodat de werkgever niet later voor een verrassing komt te
staan.

## Waarom geen scraping van Indeed/LinkedIn/etc.?

Bewuste keuze: de meeste grote vacaturesites verbieden geautomatiseerd
scrapen in hun gebruiksvoorwaarden, en scraping is te broos om
betrouwbaar wekelijks in GitHub Actions te draaien (sites veranderen hun
HTML, blokkeren bots, etc.). In plaats daarvan automatiseert dit systeem
de **selectie, scoring en boodschap** — jij (of je team) houdt de bron
van kansrijke vacatures zelf bij, wat sowieso al gebeurt via je netwerk,
mond-tot-mondreclame en handmatig zoeken.

## Bestanden in deze repository

| Bestand | Doel |
|---|---|
| `bedrijven_lijst.txt` | Lokale vertrouwde bedrijven die voorrang krijgen. Vul zelf aan. |
| `data/vacatures_bron.csv` | De "pool" van kansrijke vacatures. **Bevat nu alleen voorbeeld-/placeholderdata** — vul dit aan met echte vacatures die je vindt. |
| `data/laatst_getoond.json` | Automatisch bijgehouden staat: welke vacature wanneer al getoond is (voorkomt herhaling). Niet handmatig aanpassen. |
| `vacature_zoeker.py` | Het hoofdscript: kiest wekelijks de top 3, genereert tabel + belscript. |
| `.github/workflows/wekelijkse_vacaturezoeker.yml` | Draait het script elke maandag automatisch via GitHub Actions. |
| `output/vacatures_deze_week.md` | Wordt elke run overschreven met de nieuwste tabel — te gebruiken voor e-mail of printen. |
| `output/archief/` | Archief van elke week, zodat je terug kan kijken. |

## Zelf vacatures toevoegen

Open `data/vacatures_bron.csv` en voeg een regel toe per gevonden
vacature. Kolommen:

```
functie,bedrijf,sector,regio,telefoonnummer,contactpersoon,vacature_link,reden_urgentie,ongeschoold,datum_gevonden,actief
```

- `regio` moet "Deventer" bevatten, anders wordt de vacature genegeerd.
- `telefoonnummer` beginnend met `06` geeft een flinke boost in de score
  (direct bellen i.p.v. formulier invullen).
- `reden_urgentie`: schrijf hier zelf waarom dit bedrijf nú personeel
  zoekt (bijv. "net geopend, drie shifts onderbezet", "seizoenspiek",
  "hoog personeelsverloop"). Woorden als *spoed*, *dringend*, *per
  direct* geven extra score.
- `ongeschoold`: `ja` als er geen diploma/ervaring nodig is.
- `actief`: zet op `nee` zodra een vacature vervuld is, dan wordt hij
  niet meer meegenomen.

Zet daarnaast bedrijven die je zelf vertrouwt in `bedrijven_lijst.txt`
(zie het format bovenin dat bestand) — de bedrijfsnaam moet exact
overeenkomen met de kolom `bedrijf` in de CSV om voorrang te krijgen.

**Let op:** de huidige regels in `data/vacatures_bron.csv` zijn
fictieve voorbeelden (bedrijfsnamen met "VOORBEELD" erin, nepnummers
zoals `06-00000001`). Vervang deze door echte, door jou geverifieerde
gegevens voordat je het systeem in de praktijk gebruikt — er zijn bewust
geen verzonnen namen/telefoonnummers van bestaande bedrijven ingevuld.

## Lokaal draaien

Vereist alleen Python 3 (geen extra packages nodig):

```bash
python vacature_zoeker.py
```

Optie om te testen zonder de state/output bij te werken:

```bash
python vacature_zoeker.py --dry-run
```

Resultaat verschijnt in de terminal én (zonder `--dry-run`) in
`output/vacatures_deze_week.md`.

## Automatisch via GitHub Actions

De workflow `.github/workflows/wekelijkse_vacaturezoeker.yml` draait
elke maandagochtend automatisch, commit de nieuwe output terug naar de
repository, en opent een GitHub Issue met de tabel (handig, want je
krijgt dan een GitHub-notificatie/e-mail als je de repository "watcht").

Let op: geplande (`schedule`) GitHub Actions draaien alleen op de
**standaardbranch** van de repository. Zorg dat deze branch daar
uiteindelijk in gemerged wordt, anders draait de automatisering niet.

Je kan de workflow ook handmatig starten via het tabblad "Actions" →
"Wekelijkse vacaturezoeker" → "Run workflow".
