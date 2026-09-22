"""
Módulo de Capacidad de Infraestructura
========================================
Evalúa si la flota de camiones y las plantas de transferencia/
disposición actuales podrán absorber el volumen de residuos
proyectado, y emite alertas cuantificadas.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class Camion:
    identificador: str
    capacidad_toneladas: float
    viajes_dia: int = 2  # viajes por día que puede realizar (depende de distancia a planta)
    disponibilidad_pct: float = 0.9  # % de flota operativa (no en mantenimiento)

    def capacidad_diaria_toneladas(self) -> float:
        return self.capacidad_toneladas * self.viajes_dia * self.disponibilidad_pct


@dataclass
class PlantaTransferencia:
    nombre: str
    capacidad_diaria_toneladas: float
    horas_operacion_dia: float = 12.0


@dataclass
class FlotaYPlanta:
    camiones: List[Camion] = field(default_factory=list)
    plantas: List[PlantaTransferencia] = field(default_factory=list)

    def capacidad_flota_diaria(self) -> float:
        return sum(c.capacidad_diaria_toneladas() for c in self.camiones)

    def capacidad_plantas_diaria(self) -> float:
        return sum(p.capacidad_diaria_toneladas for p in self.plantas)

    def evaluar(self, volumen_proyectado_ton_dia: float) -> dict:
        """
        Compara el volumen proyectado contra la capacidad de flota y plantas.
        Devuelve un diagnóstico con estado (OK / ALERTA / CRÍTICO) y el % de
        utilización, para cada componente.
        """
        cap_flota = self.capacidad_flota_diaria()
        cap_plantas = self.capacidad_plantas_diaria()

        def estado(capacidad, demanda):
            if capacidad <= 0:
                return "SIN DATOS", 0.0
            utilizacion = (demanda / capacidad) * 100
            if utilizacion < 80:
                return "OK", utilizacion
            elif utilizacion < 100:
                return "ALERTA", utilizacion
            else:
                return "CRÍTICO", utilizacion

        estado_flota, uso_flota = estado(cap_flota, volumen_proyectado_ton_dia)
        estado_planta, uso_planta = estado(cap_plantas, volumen_proyectado_ton_dia)

        # déficit en toneladas/día y camiones adicionales sugeridos
        deficit_flota_ton = max(0.0, volumen_proyectado_ton_dia - cap_flota)
        camion_promedio = (
            sum(c.capacidad_diaria_toneladas() for c in self.camiones) / len(self.camiones)
            if self.camiones else 0
        )
        camiones_adicionales_sugeridos = (
            int(-(-deficit_flota_ton // camion_promedio)) if camion_promedio > 0 else None
        )  # techo (ceil) de la división

        return {
            "volumen_proyectado_ton_dia": round(volumen_proyectado_ton_dia, 2),
            "capacidad_flota_ton_dia": round(cap_flota, 2),
            "estado_flota": estado_flota,
            "utilizacion_flota_pct": round(uso_flota, 1),
            "deficit_flota_ton_dia": round(deficit_flota_ton, 2),
            "camiones_adicionales_sugeridos": camiones_adicionales_sugeridos,
            "capacidad_plantas_ton_dia": round(cap_plantas, 2),
            "estado_planta": estado_planta,
            "utilizacion_planta_pct": round(uso_planta, 1),
        }
