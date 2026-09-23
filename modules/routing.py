"""
Módulo de Optimización de Rutas
==================================
Calcula las rutas más eficientes para una flota de camiones
recolectores usando el algoritmo de Vehicle Routing Problem (VRP)
con restricción de capacidad (CVRP), vía Google OR-Tools.

Las distancias entre puntos se obtienen, en orden de preferencia:
  1. OSRM (Open Source Routing Machine) público — distancia y tiempo
     reales por calle, si hay conexión a internet.
  2. Distancia geodésica (Haversine) con un factor de corrección por
     sinuosidad vial (fallback sin internet).
"""

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

from ortools.constraint_solver import routing_enums_pb2, pywrapcp

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None


# Factor de corrección: la distancia real por calle suele ser ~1.3x
# la distancia en línea recta (varía según trazado urbano).
FACTOR_SINUOSIDAD = 1.3

# Velocidad promedio urbana asumida para camión recolector (km/h),
# considerando paradas frecuentes y tráfico moderado.
VELOCIDAD_PROMEDIO_KMH = 25.0


@dataclass
class PuntoRecoleccion:
    nombre: str
    lat: float
    lon: float
    demanda_kg: float = 0.0  # residuos a recoger en este punto


def _haversine_km(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    lat1, lon1 = p1
    lat2, lon2 = p2
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _osrm_matrix(puntos: List[PuntoRecoleccion], base_url: str = "http://router.project-osrm.org"):
    """Intenta obtener matriz de distancias reales vía OSRM público. Devuelve None si falla."""
    if requests is None:
        return None
    try:
        coords = ";".join(f"{p.lon},{p.lat}" for p in puntos)
        url = f"{base_url}/table/v1/driving/{coords}?annotations=distance,duration"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != "Ok":
            return None
        # distances en metros -> km
        dist_km = [[d / 1000.0 for d in row] for row in data["distances"]]
        dur_min = [[t / 60.0 for t in row] for row in data["durations"]]
        return dist_km, dur_min
    except Exception:
        return None


def construir_matriz_distancias(puntos: List[PuntoRecoleccion], usar_osrm: bool = True):
    """
    Devuelve (matriz_distancia_km, matriz_duracion_min, fuente) para el conjunto
    de puntos, donde el punto 0 es el depósito/planta de transferencia.
    """
    if usar_osrm:
        resultado = _osrm_matrix(puntos)
        if resultado is not None:
            dist_km, dur_min = resultado
            return dist_km, dur_min, "OSRM (calles reales)"

    # Fallback: Haversine + factor de sinuosidad
    n = len(puntos)
    dist_km = [[0.0] * n for _ in range(n)]
    dur_min = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            d = _haversine_km(
                (puntos[i].lat, puntos[i].lon), (puntos[j].lat, puntos[j].lon)
            ) * FACTOR_SINUOSIDAD
            dist_km[i][j] = d
            dur_min[i][j] = (d / VELOCIDAD_PROMEDIO_KMH) * 60
    return dist_km, dur_min, "Estimado (línea recta x1.3, sin conexión a OSRM)"


def obtener_geometria_ruta(
    secuencia_lat_lon: List[Tuple[float, float]], base_url: str = "http://router.project-osrm.org"
) -> Optional[List[Tuple[float, float]]]:
    """
    Pide a OSRM el trazado real (siguiendo calles) para una secuencia ordenada
    de puntos (lat, lon) — la ruta completa de un solo camión, en orden de
    visita. Devuelve una lista de (lat, lon) que sigue las calles reales,
    lista para dibujar con folium.PolyLine. Devuelve None si OSRM no está
    disponible o falla (el llamador debe usar línea recta como respaldo).
    """
    if requests is None or len(secuencia_lat_lon) < 2:
        return None
    try:
        coords = ";".join(f"{lon},{lat}" for lat, lon in secuencia_lat_lon)
        url = f"{base_url}/route/v1/driving/{coords}?overview=full&geometries=geojson"
        resp = requests.get(url, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != "Ok" or not data.get("routes"):
            return None
        geometria = data["routes"][0]["geometry"]["coordinates"]  # [[lon, lat], ...]
        return [(lat, lon) for lon, lat in geometria]
    except Exception:
        return None


@dataclass
class ResultadoRuta:
    vehiculo: str
    secuencia_puntos: List[str]
    distancia_total_km: float
    duracion_total_min: float
    carga_total_kg: float


@dataclass
class ResultadoOptimizacion:
    rutas: List[ResultadoRuta]
    distancia_total_flota_km: float
    fuente_distancias: str
    puntos_sin_asignar: List[str]


def optimizar_rutas(
    puntos: List[PuntoRecoleccion],
    capacidades_camiones_kg: List[float],
    usar_osrm: bool = True,
    tiempo_limite_seg: int = 10,
) -> ResultadoOptimizacion:
    """
    puntos[0] DEBE ser el depósito (planta de transferencia / base de flota).
    capacidades_camiones_kg: una entrada por camión disponible.
    """
    if len(puntos) < 2:
        raise ValueError("Se requiere al menos el depósito y un punto de recolección.")

    dist_km, dur_min, fuente = construir_matriz_distancias(puntos, usar_osrm)

    n = len(puntos)
    num_vehiculos = len(capacidades_camiones_kg)
    deposito_idx = 0

    manager = pywrapcp.RoutingIndexManager(n, num_vehiculos, deposito_idx)
    routing = pywrapcp.RoutingModel(manager)

    # Costo = distancia (escalada a metros enteros, requerido por OR-Tools)
    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return int(dist_km[from_node][to_node] * 1000)

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Restricción de capacidad
    demandas = [0] + [int(p.demanda_kg) for p in puntos[1:]]

    def demand_callback(from_index):
        from_node = manager.IndexToNode(from_index)
        return demandas[from_node]

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,  # sin holgura
        [int(c) for c in capacidades_camiones_kg],
        True,  # el vehículo empieza vacío en el depósito
        "Capacidad",
    )

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_parameters.time_limit.FromSeconds(tiempo_limite_seg)

    solution = routing.SolveWithParameters(search_parameters)

    if solution is None:
        raise RuntimeError(
            "No se encontró una solución factible: la capacidad de la flota "
            "es insuficiente para la demanda total, o los parámetros son inconsistentes."
        )

    rutas = []
    distancia_total_flota = 0.0
    puntos_visitados = set()

    for vehicle_id in range(num_vehiculos):
        index = routing.Start(vehicle_id)
        secuencia = []
        distancia_ruta = 0.0
        duracion_ruta = 0.0
        carga_ruta = 0.0
        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            secuencia.append(puntos[node].nombre)
            if node != deposito_idx:
                carga_ruta += puntos[node].demanda_kg
                puntos_visitados.add(node)
            previous_index = index
            index = solution.Value(routing.NextVar(index))
            next_node = manager.IndexToNode(index)
            distancia_ruta += dist_km[node][next_node]
            duracion_ruta += dur_min[node][next_node]
        secuencia.append(puntos[deposito_idx].nombre)  # retorno al depósito

        if len(secuencia) > 2:  # solo reportar rutas con al menos un punto real
            rutas.append(
                ResultadoRuta(
                    vehiculo=f"Camión {vehicle_id + 1}",
                    secuencia_puntos=secuencia,
                    distancia_total_km=round(distancia_ruta, 2),
                    duracion_total_min=round(duracion_ruta, 1),
                    carga_total_kg=round(carga_ruta, 1),
                )
            )
            distancia_total_flota += distancia_ruta

    no_asignados = [
        puntos[i].nombre for i in range(1, n) if i not in puntos_visitados
    ]

    return ResultadoOptimizacion(
        rutas=rutas,
        distancia_total_flota_km=round(distancia_total_flota, 2),
        fuente_distancias=fuente,
        puntos_sin_asignar=no_asignados,
    )
