"""Sistema de recomendación de reposición de inventario (analítica prescriptiva).

Flujo:  Datos -> Análisis -> Resultado -> Recomendación -> Acción

Uso:
    python src/main.py                      # sin restricción de presupuesto
    python src/main.py --presupuesto 15000  # con presupuesto limitado (MXN)
"""
import argparse
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # permite guardar la gráfica sin abrir ventana
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from generar_datos import generar

RAIZ = Path(__file__).resolve().parent.parent
DATA = RAIZ / "data"
EVIDENCIAS = RAIZ / "docs" / "evidencias"

Z_SERVICIO = 1.65        # nivel de servicio ~95 %
COSTO_MANTENER = 0.20    # costo anual de mantener inventario (20 % del costo unitario)
VENTANA_DIAS = 30        # ventana para pronosticar la demanda reciente


# ---------------------------------------------------------------- 1. DATOS
def cargar_datos():
    if not (DATA / "ventas.csv").exists():
        print("No se encontraron datos; generando dataset sintético...")
        generar()
    ventas = pd.read_csv(DATA / "ventas.csv", parse_dates=["fecha"])
    productos = pd.read_csv(DATA / "productos.csv")
    return ventas, productos


# ------------------------------------------------------------- 2. ANÁLISIS
def analizar(ventas: pd.DataFrame, productos: pd.DataFrame) -> pd.DataFrame:
    """Descriptivo + predictivo simple: demanda diaria esperada y su variabilidad."""
    recientes = ventas[ventas["fecha"] > ventas["fecha"].max() - pd.Timedelta(days=VENTANA_DIAS)]
    resumen = (
        recientes.groupby("producto")["unidades"]
        .agg(demanda_diaria="mean", desviacion="std")
        .reset_index()
    )
    return productos.merge(resumen, on="producto")


# ------------------------------------------------- 3. RESULTADO (parámetros)
def calcular_politica(df: pd.DataFrame) -> pd.DataFrame:
    d, sigma, L = df["demanda_diaria"], df["desviacion"], df["dias_entrega"]

    df["stock_seguridad"] = np.ceil(Z_SERVICIO * sigma * np.sqrt(L))
    df["punto_reorden"] = np.ceil(d * L + df["stock_seguridad"])

    demanda_anual = d * 365
    costo_mantener = COSTO_MANTENER * df["costo_unitario"]
    df["eoq"] = np.ceil(np.sqrt(2 * demanda_anual * df["costo_pedido"] / costo_mantener))

    df["dias_cobertura"] = df["stock_actual"] / d
    return df


# ------------------------------------------- 4. RECOMENDACIÓN (reglas + EOQ)
def recomendar(df: pd.DataFrame) -> pd.DataFrame:
    estados, cantidades, motivos = [], [], []
    for _, f in df.iterrows():
        if f["dias_cobertura"] < f["dias_entrega"]:
            estado = "URGENTE"
        elif f["stock_actual"] <= f["punto_reorden"]:
            estado = "PEDIR"
        else:
            estado = "OK"

        if estado == "OK":
            cantidad = 0
            motivo = (f"Stock ({f['stock_actual']:.0f}) por encima del punto de reorden "
                      f"({f['punto_reorden']:.0f}); alcanza para {f['dias_cobertura']:.1f} días.")
        else:
            cantidad = int(math.ceil(f["punto_reorden"] + f["eoq"] - f["stock_actual"]))
            motivo = (f"Stock ({f['stock_actual']:.0f}) <= punto de reorden ({f['punto_reorden']:.0f}); "
                      f"cubre {f['dias_cobertura']:.1f} días y el proveedor tarda {f['dias_entrega']:.0f}.")
            if estado == "URGENTE":
                motivo += " Se agotará antes de que llegue el pedido."
        estados.append(estado)
        cantidades.append(cantidad)
        motivos.append(motivo)

    df["estado"] = estados
    df["cantidad_sugerida"] = cantidades
    df["costo_pedido_total"] = df["cantidad_sugerida"] * df["costo_unitario"]
    df["justificacion"] = motivos
    return df


def aplicar_presupuesto(df: pd.DataFrame, presupuesto: float | None) -> pd.DataFrame:
    """Asignación de recursos: se surten primero los productos con menor cobertura."""
    df["accion"] = "No pedir"
    if presupuesto is None:
        df.loc[df["cantidad_sugerida"] > 0, "accion"] = "Pedir ahora"
        return df

    restante = presupuesto
    candidatos = df[df["cantidad_sugerida"] > 0].sort_values("dias_cobertura")
    for idx, f in candidatos.iterrows():
        if f["costo_pedido_total"] <= restante:
            df.loc[idx, "accion"] = "Pedir ahora"
            restante -= f["costo_pedido_total"]
        else:
            df.loc[idx, "accion"] = "Posponer (sin presupuesto)"
    print(f"Presupuesto: ${presupuesto:,.0f} | Ejercido: ${presupuesto - restante:,.0f} "
          f"| Restante: ${restante:,.0f}\n")
    return df


# ---------------------------------------------------------- 5. ACCIÓN (salida)
def mostrar_y_guardar(df: pd.DataFrame) -> None:
    orden = {"URGENTE": 0, "PEDIR": 1, "OK": 2}
    df = df.sort_values(by="estado", key=lambda s: s.map(orden)).reset_index(drop=True)

    cols = ["producto", "stock_actual", "demanda_diaria", "punto_reorden",
            "dias_cobertura", "estado", "cantidad_sugerida", "costo_pedido_total", "accion"]
    print(df[cols].round(1).to_string(index=False))
    print("\n--- JUSTIFICACIÓN DE LAS RECOMENDACIONES ---")
    for _, f in df[df["estado"] != "OK"].iterrows():
        print(f"* [{f['estado']}] {f['producto']}: pedir {f['cantidad_sugerida']} u. "
              f"(${f['costo_pedido_total']:,.0f}). {f['justificacion']}")

    EVIDENCIAS.mkdir(parents=True, exist_ok=True)
    df.to_csv(EVIDENCIAS / "recomendaciones.csv", index=False)
    graficar(df)
    print(f"\nResultados guardados en {EVIDENCIAS}")


def graficar(df: pd.DataFrame) -> None:
    colores = {"URGENTE": "#C0392B", "PEDIR": "#E39B2D", "OK": "#2E8B6A"}
    fig, ax = plt.subplots(figsize=(10, 5.5))
    d = df.sort_values("dias_cobertura")
    ax.barh(d["producto"], d["dias_cobertura"], color=d["estado"].map(colores))
    ax.scatter(d["dias_entrega"], d["producto"], color="black", marker="|", s=400, zorder=3)
    ax.set_xlabel("Días de cobertura del inventario actual (marca negra = días de entrega del proveedor)")
    ax.set_title("Cobertura de inventario vs. tiempo de entrega")
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in colores.values()]
    ax.legend(handles, list(colores), loc="lower right")
    plt.tight_layout()
    plt.savefig(EVIDENCIAS / "recomendaciones.png", dpi=150)
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Recomendador de reposición de inventario")
    parser.add_argument("--presupuesto", type=float, default=None,
                        help="Presupuesto disponible en MXN (opcional)")
    args = parser.parse_args()

    ventas, productos = cargar_datos()
    print(f"Datos cargados: {len(ventas):,} registros de venta, {len(productos)} productos\n")

    df = analizar(ventas, productos)
    df = calcular_politica(df)
    df = recomendar(df)
    df = aplicar_presupuesto(df, args.presupuesto)
    mostrar_y_guardar(df)


if __name__ == "__main__":
    main()
