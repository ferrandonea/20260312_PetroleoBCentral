# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Replication of Figure 1 from BCCh Working Paper N°1076 ("Inflation Heterogeneity and Differential Effects of Monetary and Oil Price Shocks", Felipe Martínez 2026). Computes household expenditure composition by income decile using microdata from Chile's VIII EPF (2016-2017, INE).

## Running

```bash
# Demo mode (no microdata needed, uses estimated values from the paper)
uv run python main.py --demo

# Real mode (requires INE microdata files in data/)
uv run python main.py
```

Real mode expects these CSV files in `data/` (from www.ine.gob.cl/epf → VIII EPF):
- `base-personas-viii-epf-(formato-csv).csv`
- `base-gastos-viii-epf-(formato-csv).csv`
- `ccif-viii-epf-(formato-csv).csv`

These files use `;` as separator and `,` as decimal (Chilean/European CSV format).

## Architecture

Single-script project (`main.py`). Pipeline:
1. Load microdata (CSV/Stata/SPSS) with `cargar_datos()` — auto-detects format by extension
2. Build weighted income deciles via `construir_deciles()` using expansion factors (`FE`)
3. Map CCIF product codes → 12 COICOP divisions (2-digit prefix)
4. Compute expenditure shares per decile with `calcular_participaciones()`
5. Generate stacked bar chart with `graficar_figura1()` — styled after BCCh/institutional charts

Outputs: `participaciones_gasto_EPF2016.csv` and `figura1_EPF2016.png`.

## Key Details

- Python 3.12, managed with uv
- Dependencies: pandas, numpy, matplotlib (not yet listed in pyproject.toml)
- Column names are uppercase to match INE's VIII EPF naming: `FOLIO`, `FE`, `ING_DISP_HOG_HD`, `GASTO`, `CCIF`
- All chart labels and category names are in Spanish
- Chart styling follows BCCh conventions: bold left-aligned title, subtitle, source/notes at bottom-left
