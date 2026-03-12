# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Replication of Figure 1 from BCCh Working Paper N°1076 ("Inflation Heterogeneity and Differential Effects of Monetary and Oil Price Shocks", Felipe Martínez 2026). Computes household expenditure composition by income decile using microdata from Chile's VIII EPF (2016-2017, INE).

## Running

```bash
# Demo mode (no microdata needed, uses estimated values from the paper)
uv run python main.py --demo

# Real mode (requires INE microdata files in project root)
uv run python main.py
```

Real mode expects these files from INE (www.ine.gob.cl/epf → VIII EPF):
- `BASE_PERSONAS_VIII_EPF.csv`
- `BASE_GASTOS_VIII_EPF.csv`
- `CCIF_VIII_EPF.csv`

## Architecture

Single-script project (`main.py`). Pipeline:
1. Load microdata (CSV/Stata/SPSS) with `cargar_datos()`
2. Build weighted income deciles via `construir_deciles()` using expansion factors
3. Map CCIF product codes → 12 COICOP divisions (2-digit prefix)
4. Compute expenditure shares per decile with `calcular_participaciones()`
5. Generate stacked bar chart with `graficar_figura1()`

Outputs: `participaciones_gasto_EPF2016.csv` and `figura1_EPF2016.png`.

## Key Details

- Python 3.12, managed with uv
- Dependencies: pandas, numpy, matplotlib (not yet listed in pyproject.toml)
- Variable names in the code (`fe`, `ing_disp_hog`, `ccif`, etc.) match INE's VIII EPF column naming
- All labels and category names use English to match the paper's figures
