# Analítica prescriptiva: ¿qué debería hacerse?
**Sistema de recomendación de reposición de inventario**

Unidad I — Fundamentos de Big Data (Manejo Masivo de Datos)
Integrantes: _(nombres del equipo)_ · Grupo IDIA 222 · UPQ

## Problema
Una tienda universitaria vende 12 productos y debe decidir **qué pedir, cuánto y cuándo** sin quedarse sin
inventario ni gastar de más. El sistema recibe el historial de ventas, lo analiza y recomienda una acción justificada.

Flujo: `Datos → Análisis → Resultado → Recomendación → Acción`

| Etapa | Qué hace el programa |
|---|---|
| Datos | Carga `ventas.csv` (4,380 registros) y `productos.csv` (inventario, tiempos de entrega, costos) |
| Análisis | Demanda diaria promedio y variabilidad de los últimos 30 días (descriptivo + pronóstico simple) |
| Resultado | Stock de seguridad, punto de reorden y cantidad económica de pedido (EOQ) |
| Recomendación | Estado por producto (URGENTE / PEDIR / OK), cantidad sugerida y justificación en texto |
| Acción | Lista de compra priorizada; con `--presupuesto` se surten primero los productos con menor cobertura |

### Fórmulas
- Stock de seguridad = Z · σ · √L (Z = 1.65, nivel de servicio ≈ 95 %)
- Punto de reorden = d · L + stock de seguridad
- EOQ = √(2 · D · S / H)
- Cantidad a pedir = punto de reorden + EOQ − stock actual

(d = demanda diaria, L = días de entrega, σ = desviación diaria, D = demanda anual, S = costo por pedido, H = costo de mantener una unidad al año.)

## Instalación
```bash
git clone <URL-DEL-REPOSITORIO>
cd proyecto-big-data
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```
Requiere Python 3.10 o superior.

## Ejecución
```bash
python src/main.py                        # recomendaciones sin límite de presupuesto
python src/main.py --presupuesto 40000    # con presupuesto de $40,000 MXN
```
Si no existen los datos, se generan automáticamente (semilla fija: siempre son los mismos).
Para regenerarlos manualmente: `python src/generar_datos.py`.

## Evidencias
En `docs/evidencias/` se guardan `recomendaciones.csv` y `recomendaciones.png` tras cada ejecución.
El diagrama de arquitectura está en `docs/arquitectura.png`.

## Limitaciones
- Los datos son sintéticos y el pronóstico es un promedio de 30 días (un modelo predictivo real podría mejorarlo).
- Se asume un solo proveedor por producto y demanda independiente entre productos.
- Es un modelo simplificado para comprender el concepto, no un sistema de producción.

## Conclusiones individuales
_(Cada integrante agrega aquí su conclusión.)_
