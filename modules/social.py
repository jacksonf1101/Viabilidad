"""
Módulo Social y Demográfico
==============================
Construye mapas de calor georreferenciados a partir de las zonas
definidas en el módulo de Generación, para identificar visualmente
qué barrios producen más residuos o tienen menores tasas de reciclaje,
y así priorizar campañas educativas.
"""

from typing import List, Tuple


def puntos_calor_generacion(zonas: List[dict]) -> List[Tuple[float, float, float]]:
    """Convierte la lista de zonas georreferenciadas en puntos (lat, lon, peso)
    para el HeatMap, donde el peso es la generación diaria en kg."""
    return [(z["lat"], z["lon"], z["generacion_kg_dia"]) for z in zonas]


def puntos_calor_deficit_reciclaje(zonas: List[dict]) -> List[Tuple[float, float, float]]:
    """Puntos ponderados por 'déficit de reciclaje': residuos generados que NO se
    reciclan (generación * (1 - tasa_reciclaje/100)). Solo aplica a zonas con
    tasa_reciclaje_pct definida (típicamente residenciales); el resto se ignora."""
    puntos = []
    for z in zonas:
        tasa = z.get("tasa_reciclaje_pct")
        if tasa is None:
            continue
        deficit_kg = z["generacion_kg_dia"] * (1 - (tasa / 100.0))
        if deficit_kg > 0:
            puntos.append((z["lat"], z["lon"], deficit_kg))
    return puntos


def ranking_zonas_por_generacion(zonas: List[dict], top_n: int = 10) -> List[dict]:
    """Devuelve las zonas ordenadas de mayor a menor generación diaria,
    útil para priorizar rutas o inversión en infraestructura."""
    return sorted(zonas, key=lambda z: z["generacion_kg_dia"], reverse=True)[:top_n]


def ranking_zonas_por_deficit_reciclaje(zonas: List[dict], top_n: int = 10) -> List[dict]:
    """Devuelve las zonas residenciales con mayor déficit de reciclaje,
    para priorizar campañas educativas."""
    con_tasa = [z for z in zonas if z.get("tasa_reciclaje_pct") is not None]
    return sorted(
        con_tasa,
        key=lambda z: z["generacion_kg_dia"] * (1 - z["tasa_reciclaje_pct"] / 100.0),
        reverse=True,
    )[:top_n]
