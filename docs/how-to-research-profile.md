# How to research or import a filament profile

This tool builds a Bambu Studio filament preset in two ways. You can **research** a filament from web pages, or **import** a profile file you already have.

**Easiest way:** double-click `_for-ezra\02-research-profile.cmd`. It asks plain questions, runs the commands below, and opens the output folder. Nothing goes into Bambu Studio unless you answer `y` at the end.

## Read this first (honest limits)

- **Nothing has been run against the live websites yet.** The tests use saved copies. Your first real run is a real test. If a site changed, you may get an error.
- The manufacturer page lists print settings (layer height, speeds, walls, infill, brim). When you give `--printer` and `--nozzle`, the tool turns the ones with an unambiguous Bambu meaning into a **process preset** next to the filament preset. On the Plant Vitamin page, 38 of the 49 items that used to be all "not mapped" now map; the other 11 stay in the report as "not mapped". Without `--printer` and `--nozzle` no process preset is written.
- The process preset has not been tried in a real Bambu Studio yet. Open it there and check the values before printing.
- Values are only as good as the sources. The report shows where every value came from.
- Installing is **opt-in** (`--install`) and **Bambu Studio must be closed**.

## Research a filament (example: TimeMass Plant Vitamin)

You need at least two sources: the manufacturer's product page, and a second profile. The second one is usually a community profile on GitHub. If you do not have one, use a profile file you already have, with `import=<file>`.

**Pick the second source to match your filament.** It should be the same kind of material and the same nozzle size. A file for a different material or nozzle fills the gaps with settings that do not fit. The example below is only right for PLA with a 0.4 nozzle.

**Say what material it is.** Add `--material-type` with the kind of material, such as `PLA`, `PETG`, `ABS`, `ASA`, `TPU`, `PA` or `PC`. The command takes any text. If you leave it out, it assumes `pla`. The launcher always asks you, so it never guesses.

```
python -m src.research_profile research --material "Plant Vitamin" --material-type PLA --manufacturer TimePlast --source "manufacturer=https://www.timeplast.com/shop/p/timemass-plant-vitamin-filament" --source "community=OrcaSlicer/OrcaSlicer:resources/profiles/BBL/filament/Bambu PLA Basic @BBL P1S 0.4 nozzle.json" --out output\research\Plant-Vitamin
```

Source kinds:
- `manufacturer=<web page address>`
- `community=<owner/repo:path to the file>` or a direct "raw" file address
- `import=<file on your computer>` (optional extra source)

**Process preset (print settings).** Add the printer and the nozzle size. Neither is assumed:

```
... --printer "Bambu Lab P1S" --nozzle 0.8
```

- The parent preset is taken from that machine's own Bambu Studio preset (`Bambu Lab P1S 0.8 nozzle` names `0.40mm Standard @BBL X1C 0.8 nozzle` as its default). It is read from your Bambu Studio install; nothing is written there. The printer name can be given with or without "Bambu Lab".
- `--parent-process "<preset name>"` picks a different parent (it must exist in Bambu Studio's system presets).
- If the printer and nozzle size do not match a Bambu Studio machine preset, the command stops with a one-line error and writes nothing.
- Speed ranges take the low end, infill density ranges the low end, and temperature ranges the midpoint. Those values are marked "derived" in the report. Everything else keeps the page's own number and is marked "published".
- Not mapped, because the meaning is not certain or Bambu has no matching key: top/bottom thickness (it conflicts with the layer count), smooth speed transition, max detour for crossing, seam position, smart scarf seam, seam angle, seam steps, flush into support. Set these by hand.
- If no source gives process settings, no process preset is written, and the report says so under "Process settings".

Useful extras: `--name "<preset name>"`, `--offline` (use saved pages only), `--cache-dir <folder>`.

**Saved pages (cache).** Every page the tool reads is saved on your computer for 7 days. Within 7 days a re-run reuses the saved copy and does not ask the site again. There is no "refresh" switch today. To get fresh data before 7 days pass, point `--cache-dir` at a different or empty folder. The launcher does not offer this; use the command line.

**Waiting.** The tool waits 5 seconds between requests to the same site, on purpose. A run with several pages from one site takes a while.

At the end it prints the output folder, how many settings the sources disagreed on ("contested"), and how many values are assumptions.

## Import a profile you already have

```
python -m src.research_profile import "C:\path\to\Your Profile.json" --out output\research\my-import
```

Optionally add `--merge-with "manufacturer=<url>"` (or `community=` or `import=`) to blend in another source. Your file wins when values clash.

Note: the importer reads Bambu Studio's own system presets from your computer (read only) to fill in inherited settings.

## What the files are

Written into the output folder:

| File | What it is |
|---|---|
| `<name>.json` | The filament preset. This is the one Bambu Studio uses. |
| `<name> process.json` | A process preset. Only written if a source had process values and you gave `--printer` and `--nozzle`. |
| `<slug>.collected.json` | Every value found, with its source. |
| `<slug>.report.md` | Read this. It shows where each value came from, which sources disagreed and who won, and the page items that were not mapped. |

**"Assumption"** means a value that no source gave. The tool filled it in from its own template for that material (named in the report). The console shows the count and the most print-relevant few; the report lists them all with their values. Check these by hand.

## Installing into Bambu Studio

Off by default. Close Bambu Studio, then add `--install` to the same command. The process preset, when there is one, is installed next to the filament preset:

```
python -m src.research_profile research ... --out output\research\Plant-Vitamin --install
```

It refuses to run while Bambu Studio is open, asks before overwriting a preset with the same name, and writes to both your account folder and the `default` folder under `%APPDATA%\BambuStudio\user`. Use `--bambu-dir <folder>` to point somewhere else (for testing).

## What can go wrong

| You see | What it means |
|---|---|
| `offline mode and not in the cache` | You used `--offline` for a page never fetched. Run once without it. |
| A "robots" message | The site asks programs not to read that page. The tool stops, on purpose. |
| Fewer than two sources | Research needs two. Add another `--source`, for example `import=<file>`. |
| Old data keeps coming back | Saved pages are reused for 7 days. Use a different or empty `--cache-dir`. |
| `no Bambu Studio machine preset named ...` | `--printer`/`--nozzle` do not match a Bambu Studio printer. Use the model as Bambu Studio shows it, for example `Bambu Lab P1S` and `0.8`. |
| `no printer and nozzle size were given` | The sources had print settings but no process preset was made. Add `--printer` and `--nozzle`. |
| Bambu Studio is running | Close it and try again. |
| GitHub says too many requests | Wait, or set the environment variable `WFT_GITHUB_TOKEN`. |
| Exit code 1 | A handled error. The message says what. Exit code 2 means a typing mistake in the command. |
