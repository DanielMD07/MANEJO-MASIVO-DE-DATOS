"""Genera datos sintéticos de una tienda universitaria (reproducibles con semilla fija).

Crea dos archivos en data/:
  - ventas.csv    : ventas diarias por producto (365 días)
  - productos.csv : catálogo con inventario actual, tiempo de entrega y costos
"""
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# nombre, demanda media diaria, tiempo de entrega (días), costo unitario (MXN),
# costo por hacer un pedido (MXN), stock actual
PRODUCTOS = [
    ("Agua 600 ml",      60, 2,   8,  40, 130),
    ("Refresco 600 ml",  45, 2,  14,  40,  70),
    ("Papas fritas",     35, 3,  12,  50, 300),
    ("Galletas",         30, 3,  10,  50, 200),
    ("Café en vaso",     40, 1,  18,  40,  30),
    ("Sándwich",         25, 1,  28,  40, 110),
    ("Cuaderno",         18, 5,  35,  80, 100),
    ("Pluma",            50, 5,   6,  80, 420),
    ("Calculadora",       4, 10, 220, 100,  35),
    ("USB 32 GB",         6, 8, 110, 100,  40),
    ("Audífonos",         5, 8, 160, 100,  25),
    ("Mochila",           3, 12, 380, 120,  55),
]


def generar(semilla: int = 42, dias: int = 365) -> None:
    rng = np.random.default_rng(semilla)
    DATA_DIR.mkdir(exist_ok=True)
    fechas = pd.date_range(end="2026-09-27", periods=dias, freq="D")
    # más ventas entre semana, menos en fin de semana
    factor_semana = np.where(fechas.dayofweek < 5, 1.15, 0.5)

    filas = []
    for i, (nombre, media, *_rest) in enumerate(PRODUCTOS):
        # algunos productos tienen tendencia creciente en los últimos meses
        tendencia = np.linspace(1.0, 1.35 if i in (1, 4, 8) else 1.0, dias)
        lam = media * factor_semana * tendencia
        unidades = rng.poisson(lam)
        filas.append(pd.DataFrame({"fecha": fechas, "producto": nombre, "unidades": unidades}))
    pd.concat(filas).to_csv(DATA_DIR / "ventas.csv", index=False)

    pd.DataFrame(
        PRODUCTOS,
        columns=["producto", "_media", "dias_entrega", "costo_unitario",
                 "costo_pedido", "stock_actual"],
    ).drop(columns="_media").to_csv(DATA_DIR / "productos.csv", index=False)
    print(f"Datos generados en {DATA_DIR}")


if __name__ == "__main__":
    generar()
