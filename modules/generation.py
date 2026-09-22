"""
Módulo de Cálculo de Generación de Residuos
=============================================
Estima la cantidad de residuos sólidos generados a partir de:
- Población residencial (kg/hab/día)
- Zonas comerciales (kg/m² o kg/local/día)
- Zonas industriales (kg/empleado/día o ton/mes fijo)

Fórmulas basadas en los índices típicos usados en estudios de
generación de residuos sólidos urbanos (PGIRS/PMGIRS) para
República Dominicana, ajustables por el usuario.
"""

from dataclasses import dataclass, field
from typing import List


# --- Índices de referencia (valores por defecto, editables en la UI) ---
# Generación per cápita típica para ciudades intermedias de RD: 0.7 - 1.2 kg/hab/día
PPC_DEFAULT = 0.9  # kg/habitante/día

# Factor de generación comercial por local promedio (kg/local/día)
COMERCIAL_DEFAULT = 15.0

# Factor de generación industrial por empleado (kg/empleado/día)
INDUSTRIAL_DEFAULT = 2.5


@dataclass
class ZonaResidencial:
    nombre: str
    poblacion: int
    ppc_kg_hab_dia: float = PPC_DEFAULT  # producción per cápita
    tasa_crecimiento_anual: float = 0.02  # 2% anual por defecto
    lat: float = 0.0
    lon: float = 0.0
    tasa_reciclaje_pct: float = 0.0  # % de los residuos de la zona que actualmente se recicla (0 = desconocido)

    def generacion_diaria_kg(self, anio_proyeccion: int = 0) -> float:
        poblacion_proyectada = self.poblacion * (
            (1 + self.tasa_crecimiento_anual) ** anio_proyeccion
        )
        return poblacion_proyectada * self.ppc_kg_hab_dia


@dataclass
class ZonaComercial:
    nombre: str
    numero_locales: int
    factor_kg_local_dia: float = COMERCIAL_DEFAULT
    lat: float = 0.0
    lon: float = 0.0

    def generacion_diaria_kg(self, anio_proyeccion: int = 0) -> float:
        # Se asume crecimiento comercial más lento (1%/año) salvo que se indique otro
        return self.numero_locales * self.factor_kg_local_dia * (1.01 ** anio_proyeccion)


@dataclass
class ZonaIndustrial:
    nombre: str
    numero_empleados: int
    factor_kg_empleado_dia: float = INDUSTRIAL_DEFAULT
    lat: float = 0.0
    lon: float = 0.0

    def generacion_diaria_kg(self, anio_proyeccion: int = 0) -> float:
        return self.numero_empleados * self.factor_kg_empleado_dia * (1.01 ** anio_proyeccion)


@dataclass
class ProyectoGeneracion:
    """Agrupa todas las zonas de un municipio/proyecto para calcular el total."""
    nombre_proyecto: str
    zonas_residenciales: List[ZonaResidencial] = field(default_factory=list)
    zonas_comerciales: List[ZonaComercial] = field(default_factory=list)
    zonas_industriales: List[ZonaIndustrial] = field(default_factory=list)

    def total_diario_kg(self, anio_proyeccion: int = 0) -> float:
        total = 0.0
        for z in self.zonas_residenciales:
            total += z.generacion_diaria_kg(anio_proyeccion)
        for z in self.zonas_comerciales:
            total += z.generacion_diaria_kg(anio_proyeccion)
        for z in self.zonas_industriales:
            total += z.generacion_diaria_kg(anio_proyeccion)
        return total

    def total_diario_toneladas(self, anio_proyeccion: int = 0) -> float:
        return self.total_diario_kg(anio_proyeccion) / 1000.0

    def total_mensual_toneladas(self, anio_proyeccion: int = 0) -> float:
        return self.total_diario_toneladas(anio_proyeccion) * 30

    def proyeccion_multianual(self, anios: int = 10) -> List[dict]:
        """Devuelve una lista de proyecciones año por año (para gráficas)."""
        resultado = []
        for a in range(anios + 1):
            resultado.append({
                "anio": a,
                "toneladas_dia": round(self.total_diario_toneladas(a), 3),
                "toneladas_mes": round(self.total_mensual_toneladas(a), 2),
            })
        return resultado

    def desglose_por_fuente(self, anio_proyeccion: int = 0) -> dict:
        res = sum(z.generacion_diaria_kg(anio_proyeccion) for z in self.zonas_residenciales)
        com = sum(z.generacion_diaria_kg(anio_proyeccion) for z in self.zonas_comerciales)
        ind = sum(z.generacion_diaria_kg(anio_proyeccion) for z in self.zonas_industriales)
        return {
            "residencial_kg": round(res, 2),
            "comercial_kg": round(com, 2),
            "industrial_kg": round(ind, 2),
        }

    def zonas_georreferenciadas(self, anio_proyeccion: int = 0) -> List[dict]:
        """Devuelve todas las zonas con coordenadas (lat/lon distintas de 0,0)
        junto con su generación diaria, para construir mapas de calor."""
        resultado = []
        for z in self.zonas_residenciales:
            if z.lat != 0.0 or z.lon != 0.0:
                resultado.append({
                    "tipo": "Residencial", "nombre": z.nombre, "lat": z.lat, "lon": z.lon,
                    "generacion_kg_dia": round(z.generacion_diaria_kg(anio_proyeccion), 2),
                    "tasa_reciclaje_pct": z.tasa_reciclaje_pct,
                })
        for z in self.zonas_comerciales:
            if z.lat != 0.0 or z.lon != 0.0:
                resultado.append({
                    "tipo": "Comercial", "nombre": z.nombre, "lat": z.lat, "lon": z.lon,
                    "generacion_kg_dia": round(z.generacion_diaria_kg(anio_proyeccion), 2),
                    "tasa_reciclaje_pct": None,
                })
        for z in self.zonas_industriales:
            if z.lat != 0.0 or z.lon != 0.0:
                resultado.append({
                    "tipo": "Industrial", "nombre": z.nombre, "lat": z.lat, "lon": z.lon,
                    "generacion_kg_dia": round(z.generacion_diaria_kg(anio_proyeccion), 2),
                    "tasa_reciclaje_pct": None,
                })
        return resultado
