"""
Replicación de Figura 1 - Working Paper BCCh N°1076
"Inflation Heterogeneity and Differential Effects of Monetary and Oil Price Shocks"
Felipe Martínez (2026)

Este script calcula la composición del gasto de los hogares por decil de ingreso
usando los microdatos de la VIII EPF (julio 2016 - junio 2017) del INE Chile.

ARCHIVOS NECESARIOS (descargar desde www.ine.gob.cl/epf → VIII EPF):
  - BASE_PERSONAS_VIII_EPF.csv  (o .dta / .sav)
  - BASE_GASTOS_VIII_EPF.csv    (o .dta / .sav)
  - CCIF_VIII_EPF.csv           (clasificador de productos)

REQUISITOS:
  pip install pandas numpy matplotlib seaborn

ESTRUCTURA ESPERADA DE LAS BASES:
  Base Personas: folio, factor_expansion, ingreso_total_hogar (o similar)
  Base Gastos:   folio, codigo_ccif, gasto_mensual (o similar)
  Base CCIF:     codigo_producto, division (2 dígitos), nombre_division
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os
import sys

# =============================================================================
# 1. CONFIGURACIÓN DE RUTAS
# =============================================================================

# Modifica estas rutas según dónde guardes los archivos del INE
RUTA_PERSONAS = "data/base-personas-viii-epf-(formato-csv).csv"
RUTA_GASTOS   = "data/base-gastos-viii-epf-(formato-csv).csv"
RUTA_CCIF     = "data/ccif-viii-epf-(formato-csv).csv"

# Nombres de variables clave — verificar en el Manual de Usuarios del INE
# (pueden variar ligeramente según la versión descargada)
VAR_FOLIO        = "FOLIO"           # Identificador único del hogar
VAR_FACTOR_EXP   = "FE"              # Factor de expansión (ponderador)
VAR_INGRESO      = "ING_DISP_HOG_HD" # Ingreso disponible total del hogar
VAR_GASTO        = "GASTO"           # Gasto mensual del producto
VAR_COD_CCIF     = "CCIF"            # Código del producto (CCIF)

# =============================================================================
# 2. CARGA DE DATOS
# =============================================================================

def cargar_datos(ruta, formato="csv", **kwargs):
    """Carga un archivo en formato CSV, Stata o SPSS."""
    if not os.path.exists(ruta):
        raise FileNotFoundError(
            f"\n❌ Archivo no encontrado: {ruta}\n"
            f"   Descarga los microdatos desde: https://www.ine.gob.cl/epf\n"
            f"   Sección: VIII EPF (julio 2016 – junio 2017) → Bases de datos"
        )
    ext = os.path.splitext(ruta)[1].lower()
    if ext == ".csv":
        return pd.read_csv(ruta, sep=";", decimal=",", **kwargs)
    elif ext in (".dta",):
        return pd.read_stata(ruta, **kwargs)
    elif ext in (".sav",):
        return pd.read_spss(ruta, **kwargs)
    else:
        raise ValueError(f"Formato no soportado: {ext}. Usar .csv, .dta o .sav")


print("=" * 60)
print("Cargando microdatos VIII EPF 2016...")
print("=" * 60)

try:
    df_personas = cargar_datos(RUTA_PERSONAS)
    df_gastos   = cargar_datos(RUTA_GASTOS)
    df_ccif     = cargar_datos(RUTA_CCIF)
    print(f"✓ Personas: {len(df_personas):,} registros")
    print(f"✓ Gastos:   {len(df_gastos):,} registros")
    print(f"✓ CCIF:     {len(df_ccif):,} ítems")
except FileNotFoundError as e:
    print(e)
    print("\n⚠️  Para pruebas sin los datos reales, ejecuta con --demo")
    if "--demo" not in sys.argv:
        sys.exit(1)
    df_personas = df_gastos = df_ccif = None

# =============================================================================
# 3. PREPARACIÓN: DECILES DE INGRESO
# =============================================================================

def construir_deciles(df_personas, var_folio, var_ingreso, var_factor):
    """
    Construye deciles de ingreso usando el factor de expansión (ponderado).
    El paper usa ingreso total del hogar para ordenar los deciles,
    construido de forma independiente para cada ola de la EPF.
    """
    df = df_personas[[var_folio, var_ingreso, var_factor]].copy()
    df = df.dropna(subset=[var_ingreso])
    df = df[df[var_ingreso] > 0]

    # Deciles ponderados por factor de expansión
    df = df.sort_values(var_ingreso)
    df["peso_acum"] = df[var_factor].cumsum()
    peso_total = df[var_factor].sum()
    df["pct_acum"] = df["peso_acum"] / peso_total

    cortes = np.linspace(0, 1, 11)
    df["decil"] = pd.cut(
        df["pct_acum"],
        bins=cortes,
        labels=[f"D{i}" for i in range(1, 11)],
        include_lowest=True
    )
    return df[[var_folio, "decil", var_factor]]


# =============================================================================
# 4. CLASIFICACIÓN CCIF → DIVISIÓN COICOP
# =============================================================================

# Mapeo de divisiones COICOP (2 dígitos) a nombres legibles
# Según la adaptación del INE Chile para la VIII EPF
DIVISIONES = {
    "01": "Alimentos y beb.",
    "02": "Beb. alcohólicas",
    "03": "Vestuario",
    "04": "Vivienda y serv.",
    "05": "Equipamiento hogar",
    "06": "Salud",
    "07": "Transporte",
    "08": "Comunicaciones",
    "09": "Recreación",
    "10": "Educación",
    "11": "Restaurantes",
    "12": "Otros",
}

def extraer_division(codigo_ccif):
    """
    Extrae los 2 primeros dígitos del código CCIF para obtener la división.
    El código CCIF en la EPF tiene formato: DD.G.C.SS.PP
    donde DD = división (2 dígitos)
    """
    codigo_str = str(codigo_ccif).strip().zfill(10)
    return codigo_str[:2]


# =============================================================================
# 5. CÁLCULO DE PARTICIPACIONES DE GASTO POR DECIL
# =============================================================================

def calcular_participaciones(df_personas, df_gastos, var_folio, var_ingreso,
                              var_factor, var_gasto, var_ccif):
    """
    Calcula la participación de cada división COICOP en el gasto total,
    por decil de ingreso, usando factores de expansión.

    Metodología del paper:
    - Los pesos se calculan como gasto expandido (gasto × fe) por categoría
    - La participación de cada categoría = gasto_cat / gasto_total del decil
    """
    # Construir deciles
    df_deciles = construir_deciles(df_personas, var_folio, var_ingreso, var_factor)

    # Unir gastos con deciles y factor de expansión
    df = df_gastos[[var_folio, var_ccif, var_gasto]].merge(
        df_deciles, on=var_folio, how="inner"
    )

    # Extraer división COICOP
    df["division"] = df[var_ccif].apply(extraer_division)
    df["nombre_div"] = df["division"].map(DIVISIONES).fillna("Other")

    # Gasto expandido (ponderado por factor de expansión)
    df["gasto_exp"] = df[var_gasto] * df[var_factor]

    # Gasto total por decil
    gasto_total_decil = (
        df.groupby("decil")["gasto_exp"].sum().rename("gasto_total_decil")
    )

    # Gasto por decil y división
    gasto_div = (
        df.groupby(["decil", "nombre_div"])["gasto_exp"]
        .sum()
        .reset_index()
    )

    # Unir y calcular participación
    gasto_div = gasto_div.merge(gasto_total_decil, on="decil")
    gasto_div["participacion"] = (
        gasto_div["gasto_exp"] / gasto_div["gasto_total_decil"] * 100
    )

    # Pivot: filas = divisiones, columnas = deciles
    tabla = gasto_div.pivot(
        index="nombre_div", columns="decil", values="participacion"
    ).fillna(0)

    # Ordenar columnas de D1 a D10
    deciles_orden = [f"D{i}" for i in range(1, 11)]
    tabla = tabla.reindex(columns=deciles_orden, fill_value=0)

    return tabla


# =============================================================================
# 6. GRÁFICO: REPLICACIÓN DE FIGURA 1
# =============================================================================

# Orden y colores según el gráfico original del paper
ORDEN_CATEGORIAS = [
    "Alimentos y beb.",
    "Vivienda y serv.",
    "Transporte",
    "Educación",
    "Beb. alcohólicas",
    "Equipamiento hogar",
    "Comunicaciones",
    "Restaurantes",
    "Vestuario",
    "Salud",
    "Recreación",
    "Otros",
]

COLORES = {
    "Alimentos y beb.":     "#1F4E79",   # azul oscuro
    "Vivienda y serv.":     "#F4A322",   # naranja
    "Transporte":           "#A8B9D5",   # azul claro / lavanda
    "Educación":            "#BDC3C7",   # gris claro
    "Beb. alcohólicas":     "#8B0000",   # rojo oscuro
    "Equipamiento hogar":   "#A8C5A0",   # verde oliva claro
    "Comunicaciones":       "#D4C27A",   # amarillo arena
    "Restaurantes":         "#1C7B6B",   # verde petróleo
    "Vestuario":            "#2ECC71",   # verde claro
    "Salud":                "#E74C3C",   # rojo vivo
    "Recreación":           "#C0392B",   # café rojizo
    "Otros":                "#7D6608",   # marrón dorado
}


def graficar_figura1(tabla, titulo="Canastas de consumo por decil de ingreso",
                     subtitulo="VIII EPF (julio 2016 – junio 2017)",
                     fuente="Fuente: Elaboración propia en base a microdatos VIII EPF, INE Chile.",
                     guardar_como="figura1_EPF2016.png"):
    """Genera el gráfico de barras apiladas replicando la Figura 1 del paper."""

    deciles = [f"D{i}" for i in range(1, 11)]
    categorias = [c for c in ORDEN_CATEGORIAS if c in tabla.index]

    fig, ax = plt.subplots(figsize=(12, 6), facecolor="white")
    ax.set_facecolor("white")

    base = np.zeros(len(deciles))
    barras = {}

    for cat in categorias:
        valores = tabla.reindex(categorias).loc[cat, deciles].values
        barras[cat] = ax.bar(
            deciles,
            valores,
            bottom=base,
            color=COLORES.get(cat, "#999999"),
            label=cat,
            width=0.65,
            edgecolor="white",
            linewidth=0.3
        )
        base += valores

    # Estilo — inspirado en gráficos BCCh
    ax.set_ylim(0, 105)
    ax.set_ylabel("Porcentaje", fontsize=11, color="#333333")
    ax.set_xlabel("")

    # Título en negrita + subtítulo más pequeño
    ax.set_title(titulo, fontsize=13, fontweight="bold", color="#222222",
                 loc="left", pad=20)
    ax.text(0.0, 1.02, subtitulo, transform=ax.transAxes,
            fontsize=10, color="#666666", va="bottom")

    ax.tick_params(axis="both", labelsize=10, colors="#333333")

    # Spines finos y grises (todos visibles)
    for spine in ax.spines.values():
        spine.set_color("#CCCCCC")
        spine.set_linewidth(0.8)

    # Grid horizontal punteado
    ax.yaxis.grid(True, alpha=0.4, linestyle="--", color="#CCCCCC")
    ax.xaxis.grid(False)
    ax.set_axisbelow(True)

    # Leyenda en 3 columnas debajo del gráfico
    handles = [
        mpatches.Patch(color=COLORES.get(c, "#999999"), label=c)
        for c in categorias
    ]
    ax.legend(
        handles=handles,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.10),
        ncol=4,
        fontsize=9,
        frameon=False,
        labelcolor="#333333"
    )

    plt.tight_layout()

    # Pie: fuente y nota (debajo de la leyenda, fuera del tight_layout)
    nota = "Nota: D1 corresponde al decil de menor ingreso y D10 al de mayor ingreso."
    pie = f"{fuente}\n{nota}"
    fig.text(0.06, -0.01, pie, fontsize=8.5, color="#666666",
             va="top", ha="left", linespacing=1.5)

    plt.savefig(guardar_como, dpi=150, bbox_inches="tight", facecolor="white")
    print(f"\n✓ Gráfico guardado: {guardar_como}")
    plt.show()
    return fig


# =============================================================================
# 7. EJECUCIÓN PRINCIPAL
# =============================================================================

if __name__ == "__main__":

    DEMO_MODE = "--demo" in sys.argv or df_personas is None

    if DEMO_MODE:
        # ----------------------------------------------------------------
        # MODO DEMO: usa los valores estimados visualmente del paper
        # para verificar que el gráfico funciona correctamente
        # ----------------------------------------------------------------
        print("\n⚠️  Ejecutando en modo DEMO con valores estimados del gráfico.")
        print("   Para datos exactos, descarga los microdatos del INE y")
        print("   ejecuta sin el flag --demo.\n")

        datos_demo = {
            "Alimentos y beb.":     [26,26,26,24,22,20,18,17,14,10],
            "Vivienda y serv.":     [23,23,22,20,18,17,16,14,13,12],
            "Transporte":           [10,11,12,13,15,16,17,18,19,20],
            "Educación":            [ 3, 3, 3, 3, 3, 3, 3, 3, 3, 3],
            "Beb. alcohólicas":     [ 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
            "Equipamiento hogar":   [ 5, 5, 5, 5, 5, 5, 6, 6, 6, 7],
            "Comunicaciones":       [ 4, 4, 4, 4, 4, 4, 4, 4, 5, 5],
            "Restaurantes":         [ 4, 4, 4, 5, 5, 5, 5, 5, 6, 6],
            "Vestuario":            [ 4, 4, 4, 4, 4, 5, 5, 5, 6, 7],
            "Salud":                [ 5, 5, 5, 5, 5, 6, 7, 8, 7, 7],
            "Recreación":           [ 4, 4, 4, 5, 6, 6, 7, 8, 8, 9],
            "Otros":                [11,10,10,11,12,12,11,11,12,13],
        }

        deciles = [f"D{i}" for i in range(1, 11)]
        tabla = pd.DataFrame(datos_demo, index=deciles).T
        tabla.columns.name = "decil"

    else:
        # ----------------------------------------------------------------
        # MODO REAL: procesa los microdatos del INE
        # ----------------------------------------------------------------
        print("\nProcesando microdatos...")

        # ⚠️ Ajusta los nombres de variables si difieren en tu versión
        # Revisa el Manual de Usuarios de la VIII EPF del INE para confirmar
        tabla = calcular_participaciones(
            df_personas=df_personas,
            df_gastos=df_gastos,
            var_folio=VAR_FOLIO,
            var_ingreso=VAR_INGRESO,
            var_factor=VAR_FACTOR_EXP,
            var_gasto=VAR_GASTO,
            var_ccif=VAR_COD_CCIF,
        )

    # Mostrar tabla
    print("\nParticipaciones de gasto por decil (%):")
    print("-" * 60)
    print(tabla.round(1).to_string())

    # Verificar sumas por decil
    print("\nSuma por decil (debe ser ~100%):")
    print(tabla.sum().round(1).to_string())

    # Exportar a CSV
    tabla.to_csv("participaciones_gasto_EPF2016.csv", float_format="%.2f")
    print("\n✓ Tabla exportada: participaciones_gasto_EPF2016.csv")

    # Generar gráfico
    graficar_figura1(
        tabla,
        titulo="Figura 1: Canastas de consumo por decil de ingreso",
        subtitulo="Replicación Working Paper BCCh N°1076 — VIII EPF (julio 2016 – junio 2017)",
        guardar_como="figura1_EPF2016.png"
    )

    print("\n✅ Proceso completado.")