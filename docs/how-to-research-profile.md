# How to research or import a filament profile

This tool builds a Bambu Studio filament preset in two ways. You can **research** a filament from web pages, or **import** a profile file you already have.

**Easiest way:** double-click `_for-ezra\02-research-profile.cmd`. It asks plain questions, runs the commands below, and opens the output folder. Nothing goes into Bambu Studio unless you answer `y` at the end.

## Read this first (honest limits)

- **Nothing has been run against the live websites yet.** The tests use saved copies. Your first real run is a real test. If a site changed, you may get an error.
- The two web sources give you a **filament preset only**. There is no process (print settings) preset. The page's print settings are listed as "not mapped" in the report. A process preset only appears if one of your sources carries process values, such as an imported file.
- Values are only as good as the sources. The report shows where every value came from.
- Installing is **opt-in** (`--install`) and **Bambu Studio must be closed**.

## Research a filament (example: TimeMass Plant Vitamin)

You need at least two sources: the manufacturer's product page, and a community profile on GitHub.

```
python -m src.research_profile research --material "Plant Vitamin" --manufacturer TimePlast --source "manufacturer=https://www.timeplast.com/shop/p/timemass-plant-vitamin-filament" --source "community=OrcaSlicer/OrcaSlicer:resources/profiles/BBL/filament/Bambu PLA Basic @BBL P1S 0.4 nozzle.json" --out output\research\Plant-Vitamin
```

Source kinds:
- `manufacturer=<web page address>`
- `community=<owner/repo:path to the file>` or a direct "raw" file address
- `import=<file on your computer>` (optional extra source)

Useful extras: `--name "<preset name>"`, `--offline` (use saved pages only), `--cache-dir <folder>`.

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
| `<name> process.json` | A process preset. Only written if a source had process values. |
| `<slug>.collected.json` | Every value found, with its source. |
| `<slug>.report.md` | Read this. It shows where each value came from, which sources disagreed and who won, and the page items that were not mapped. |

**"Assumption"** means a value that no source gave. The tool filled it in with a default. Check these by hand.

## Installing into Bambu Studio

Off by default. Close Bambu Studio, then add `--install` to the same command:

```
python -m src.research_profile research ... --out output\research\Plant-Vitamin --install
```

It refuses to run while Bambu Studio is open, asks before overwriting a preset with the same name, and writes to both your account folder and the `default` folder under `%APPDATA%\BambuStudio\user`. Use `--bambu-dir <folder>` to point somewhere else (for testing).

## What can go wrong

| You see | What it means |
|---|---|
| `offline mode and not in the cache` | You used `--offline` for a page never fetched. Run once without it. |
| A "robots" message | The site asks programs not to read that page. The tool stops, on purpose. |
| Fewer than two sources | Research needs two. Add another `--source`. |
| Bambu Studio is running | Close it and try again. |
| GitHub says too many requests | Wait, or set the environment variable `WFT_GITHUB_TOKEN`. |
| Exit code 1 | A handled error. The message says what. Exit code 2 means a typing mistake in the command. |
