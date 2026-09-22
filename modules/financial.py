"""
Módulo Económico y Financiero
================================
- Análisis costo-beneficio: costo por tonelada vs. ingresos por
  venta de reciclables y/o biogás.
- Simulación de tarifas: tarifa de equilibrio para autosostenibilidad.
- ROI: años de recuperación de la inversión en camiones/plantas.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CostoOperativo:
    concepto: str  # ej. Combustible, Mano de obra, Mantenimiento, Disposición final
    monto_mensual: float


@dataclass
class MaterialReciclable:
    nombre: str  # ej. Plástico, Vidrio, Cartón, Metal
    porcentaje_del_total: float  # % de los residuos totales que es este material recuperable
    precio_venta_kg: float  # RD$/kg (o la moneda que use el usuario)


@dataclass
class ProyectoFinanciero:
    nombre_proyecto: str
    costos_operativos: List[CostoOperativo] = field(default_factory=list)
    materiales_reciclables: List[MaterialReciclable] = field(default_factory=list)
    ingreso_biogas_mensual: float = 0.0
    numero_usuarios: int = 0  # hogares/empresas que pagarán la tarifa de aseo
    tarifa_mensual_por_usuario: float = 0.0  # tarifa a evaluar (puede ser la de equilibrio u otra)
    inversion_inicial: float = 0.0  # RD$ invertidos en camiones/planta

    # --- Costos ---
    def costos_totales_mensuales(self) -> float:
        return sum(c.monto_mensual for c in self.costos_operativos)

    def costo_por_tonelada(self, toneladas_mes_total: float) -> float:
        if toneladas_mes_total <= 0:
            return 0.0
        return self.costos_totales_mensuales() / toneladas_mes_total

    # --- Ingresos ---
    def ingresos_reciclables_mensuales(self, toneladas_mes_total: float) -> float:
        total = 0.0
        for m in self.materiales_reciclables:
            kg_recuperados = toneladas_mes_total * 1000 * (m.porcentaje_del_total / 100)
            total += kg_recuperados * m.precio_venta_kg
        return total

    def recaudo_tarifas_mensual(self) -> float:
        return self.tarifa_mensual_por_usuario * self.numero_usuarios

    def ingresos_totales_mensuales(self, toneladas_mes_total: float) -> float:
        return (
            self.ingresos_reciclables_mensuales(toneladas_mes_total)
            + self.ingreso_biogas_mensual
            + self.recaudo_tarifas_mensual()
        )

    # --- Balance y tarifa de equilibrio ---
    def balance_mensual(self, toneladas_mes_total: float) -> float:
        return self.ingresos_totales_mensuales(toneladas_mes_total) - self.costos_totales_mensuales()

    def tarifa_equilibrio_por_usuario(self, toneladas_mes_total: float) -> Optional[float]:
        """Tarifa mensual por usuario necesaria para que ingresos = costos (balance = 0),
        sin contar la tarifa actualmente cargada. Devuelve None si no hay usuarios."""
        if self.numero_usuarios <= 0:
            return None
        ingresos_sin_tarifa = (
            self.ingresos_reciclables_mensuales(toneladas_mes_total) + self.ingreso_biogas_mensual
        )
        deficit = self.costos_totales_mensuales() - ingresos_sin_tarifa
        return max(0.0, deficit / self.numero_usuarios)

    # --- ROI ---
    def roi_anios(self, toneladas_mes_total: float) -> Optional[float]:
        """Años para recuperar la inversión inicial, según el balance mensual actual
        (con la tarifa_mensual_por_usuario configurada). None si el balance no es positivo
        (el proyecto no se autofinancia con estos parámetros, nunca se recupera)."""
        if self.inversion_inicial <= 0:
            return 0.0
        balance = self.balance_mensual(toneladas_mes_total)
        if balance <= 0:
            return None
        return self.inversion_inicial / (balance * 12)

    def resumen(self, toneladas_mes_total: float) -> dict:
        return {
            "costos_totales_mensuales": round(self.costos_totales_mensuales(), 2),
            "costo_por_tonelada": round(self.costo_por_tonelada(toneladas_mes_total), 2),
            "ingresos_reciclables_mensuales": round(
                self.ingresos_reciclables_mensuales(toneladas_mes_total), 2
            ),
            "ingreso_biogas_mensual": round(self.ingreso_biogas_mensual, 2),
            "recaudo_tarifas_mensual": round(self.recaudo_tarifas_mensual(), 2),
            "ingresos_totales_mensuales": round(
                self.ingresos_totales_mensuales(toneladas_mes_total), 2
            ),
            "balance_mensual": round(self.balance_mensual(toneladas_mes_total), 2),
            "tarifa_equilibrio_por_usuario": (
                round(t, 2) if (t := self.tarifa_equilibrio_por_usuario(toneladas_mes_total)) is not None
                else None
            ),
            "roi_anios": (
                round(r, 2) if (r := self.roi_anios(toneladas_mes_total)) is not None else None
            ),
        }
