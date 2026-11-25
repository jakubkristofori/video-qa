# video-qa

[![CI](https://github.com/jakubkristofori/video-qa/actions/workflows/ci.yml/badge.svg)](https://github.com/jakubkristofori/video-qa/actions)

Automatická kontrola kvality videí **čistě skriptem** (ffprobe/ffmpeg + pytest), bez AI agenta.
Výsledek je deterministický: stejný vstup dá vždy stejný verdikt, takže se kontrola dá pustit v CI
a použít jako *quality gate* před publikací.

## Co se kontroluje

| Oblast | Kontroly |
|---|---|
| Technické parametry | rozlišení, FPS, kodek, pix_fmt, audio kodek a vzorkování, počet audio stop, délka, velikost |
| Zvuk | integrovaná hlasitost (LUFS), true peak (klipování), ticho na začátku a konci |
| Obraz | černé úseky (`blackdetect`), zamrzlý obraz (`freezedetect`) |
| Soubory | existence a neprázdnost video / náhled / titulky, rozlišení a velikost náhledu |
| Metadata | délka titulku, popis, tagy, jazyk, explicitní `made_for_kids` |

Každá kontrola vrací `pass` / `fail` / `warn` / `skip`. Při jakémkoli `fail` je exit code `1`.
Reporty: konzole, JSON, JUnit XML a HTML (`reports/`).

## Použití

```bash
pip install -e ".[dev]"          # potřebuje nainstalovaný ffmpeg
video-qa episodes/tutu-ep01      # nebo: just qa episodes/tutu-ep01
```

Každá epizoda je složka s `config.yaml` (viz `episodes/example/config.yaml`). Prahy mají výchozí
hodnoty v `src/video_qa/default_spec.yaml` a v configu epizody je lze přepsat.

Volby, které vznikly při nasazení na skutečné epizody:

- `video.allow_black_at_end_s` – toleruje stmívání do černé v posledních N sekundách (úsek musí končit s videem;
  černá uprostřed videa se dál hlásí).
- `metadata.require_tags: false` – pro Shorts bez tagů; limit délky tagů platí dál.
- `video.max_freeze_s` – statická „je řada na tobě“ obrazovka v kvízech trvá i 6 s, takže se ladí po sériích.

## Strategie testování

- **Unit/integrační testy** (`tests/`) generují přes ffmpeg syntetická videa: jedno dobré a
  záměrně vadné vzorky (černý úsek, zamrzlý obraz, klipování, příliš tichý zvuk, ticho na okrajích,
  špatné FPS a rozlišení, chybějící audio). Každá kontrola má pozitivní i negativní test, takže
  je ověřené, že *skutečně chytá* vady, ne jen že běží.
- **CI** (`.github/workflows/ci.yml`): ruff + pytest na Pythonu 3.11 a 3.13, uložení reportů jako
  artefaktů a shrnutí v GitHub Actions. Ruční spuštění (`workflow_dispatch`) umí zkontrolovat konkrétní epizodu.
- **Quality gate**: v nastavení repa zapni branch protection a požaduj úspěšný job `test`.
- **GitLab** (`.gitlab-ci.yml`): GitHub Action `mirror-gitlab.yml` zrcadlí každý push na GitLab, kde běží stejné testy
  s JUnit reporty v záložce *Tests*.
- **QA skutečných epizod** (job `episode-qa`, `ci/weekly_qa.py`): běží na **self-hosted GitLab Runneru** přímo na PC
  s videi (tag `video-pc`, jen chráněné větve). Videa PC neopouští – na GitLab jdou jen JUnit a HTML reporty
  s odstraněnými lokálními cestami. Plán každý pátek 8:00 kontroluje videa změněná za posledních 7 dní,
  ručně jde spustit jedna epizoda (`EPISODE=<složka>`) nebo všechno (`QA_DAYS=0`).

## Struktura

```
src/video_qa/
  checks/        technical.py, audio.py, video.py, files.py, metadata.py
  runner.py      složí kontroly pro jednu epizodu
  report.py      JSON / JUnit / HTML / konzole
  cli.py         příkaz video-qa
tests/           pytest + generátor syntetických videí (conftest.py)
episodes/        konfigurace epizod
```

## Možná rozšíření

Kontrola titulků (formát a časování `.srt`), konzistence postav přes embeddingy s pevným prahem,
JSON Schema pro `config.yaml`, pre-commit hook, Allure report.
