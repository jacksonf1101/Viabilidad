"""
Módulo Ambiental
===================
- Huella de carbono: CO2 evitado por reciclaje y por optimización de rutas.
- Lixiviados: balance hídrico simplificado según precipitación y área del relleno.
- Gases de relleno sanitario: modelo LandGEM (EPA) para generación de metano.

IMPORTANTE: los factores de emisión y los parámetros de LandGEM incluidos
como valores "por defecto" son valores típicos de referencia usados en la
literatura técnica (EPA LandGEM, IPCC), NO constituyen un estudio de
caracterización específico del sitio. Deben ajustarse con datos reales
(estudio de caracterización de residuos, datos climáticos locales) para
cualquier uso regulatorio o de ingeniería de detalle.
"""

import math
from dataclasses import dataclass, field
from typing import List, Optional


# --- Factores de emisión evitada por reciclaje (kg CO2eq evitado por kg de material) ---
# Valores de referencia típicos (orden de magnitud EPA WARM); ajustables por el usuario.
FACTORES_EMISION_DEFAULT = {
    "Plástico": 1.6,
    "Papel/Cartón": 3.6,
    "Vidrio": 0.3,
    "Metal (aluminio)": 9.0,
    "Metal (general)": 2.0,
    "Orgánico (compostaje)": 0.2,
}

# Emisión de CO2 por litro de diésel quemado (kg CO2/L) — factor estándar de combustión
FACTOR_EMISION_DIESEL_KG_CO2_POR_L = 2.68

# Potencial de calentamiento global del metano a 100 años (IPCC AR5)
GWP_METANO = 28


@dataclass
class MaterialEmisionEvitada:
    nombre: str
    kg_mensuales_reciclados: float
    factor_kg_co2_por_kg: float


@dataclass
class HuellaCarbono:
    materiales: List[MaterialEmisionEvitada] = field(default_factory=list)
    # Optimización de rutas
    distancia_sin_optimizar_km_dia: float = 0.0
    distancia_optimizada_km_dia: float = 0.0
    consumo_diesel_l_por_km: float = 0.35  # típico camión recolector: 0.3-0.45 L/km
    dias_operacion_mes: int = 26

    def co2_evitado_reciclaje_kg_mes(self) -> float:
        return sum(m.kg_mensuales_reciclados * m.factor_kg_co2_por_kg for m in self.materiales)

    def km_ahorrados_dia(self) -> float:
        return max(0.0, self.distancia_sin_optimizar_km_dia - self.distancia_optimizada_km_dia)

    def diesel_ahorrado_l_mes(self) -> float:
        return self.km_ahorrados_dia() * self.consumo_diesel_l_por_km * self.dias_operacion_mes

    def co2_evitado_rutas_kg_mes(self) -> float:
        return self.diesel_ahorrado_l_mes() * FACTOR_EMISION_DIESEL_KG_CO2_POR_L

    def co2_evitado_total_kg_mes(self) -> float:
        return self.co2_evitado_reciclaje_kg_mes() + self.co2_evitado_rutas_kg_mes()

    def resumen(self) -> dict:
        total_mes = self.co2_evitado_total_kg_mes()
        return {
            "co2_evitado_reciclaje_kg_mes": round(self.co2_evitado_reciclaje_kg_mes(), 1),
            "km_ahorrados_dia": round(self.km_ahorrados_dia(), 2),
            "diesel_ahorrado_l_mes": round(self.diesel_ahorrado_l_mes(), 1),
            "co2_evitado_rutas_kg_mes": round(self.co2_evitado_rutas_kg_mes(), 1),
            "co2_evitado_total_kg_mes": round(total_mes, 1),
            "co2_evitado_total_ton_anio": round(total_mes * 12 / 1000, 2),
        }


@dataclass
class ParametrosLixiviado:
    """Balance hídrico simplificado (método del coeficiente de infiltración),
    útil para una estimación de orden de magnitud del caudal de lixiviado."""
    area_relleno_m2: float
    precipitacion_anual_mm: float
    coeficiente_infiltracion_pct: float = 20.0  # % de la lluvia que se infiltra y se convierte en lixiviado
    # (típicamente 15-25% con cobertura final adecuada; puede superar 40% sin cobertura)

    def volumen_lixiviado_anual_m3(self) -> float:
        # 1 mm de lluvia sobre 1 m2 = 1 litro = 0.001 m3
        precipitacion_m3 = self.area_relleno_m2 * (self.precipitacion_anual_mm / 1000.0)
        return precipitacion_m3 * (self.coeficiente_infiltracion_pct / 100.0)

    def caudal_promedio_m3_dia(self) -> float:
        return self.volumen_lixiviado_anual_m3() / 365.0

    def resumen(self) -> dict:
        return {
            "volumen_lixiviado_anual_m3": round(self.volumen_lixiviado_anual_m3(), 1),
            "caudal_promedio_m3_dia": round(self.caudal_promedio_m3_dia(), 2),
        }


@dataclass
class ParametrosLandGEM:
    """Modelo LandGEM (EPA) de primer orden para generación de metano en rellenos sanitarios.

        Q_CH4(t) = Σ_i  k · L0 · (M_i) · exp(-k · (t - t_i))

    donde:
        Q_CH4(t): tasa de generación de metano en el año t (m3/año)
        k:        constante de decaimiento (1/año) — depende de humedad/clima
        L0:       capacidad potencial de generación de metano (m3 CH4/Mg de residuo)
        M_i:      masa de residuos dispuestos en el año i (Mg = toneladas)
        t_i:      año en que se dispuso M_i
    """
    k_decaimiento_anual: float = 0.05  # valor típico EPA para clima húmedo/tropical
    l0_m3_ch4_por_mg: float = 100.0  # valor típico EPA (rango habitual 65-170)

    def generacion_metano_m3_anio(
        self, masas_anuales_ton: List[float], anio_evaluacion: int
    ) -> float:
        """masas_anuales_ton[i] = toneladas dispuestas en el año i (i=0 es el primer año
        de operación del relleno). anio_evaluacion: año (índice) en el que se calcula
        la generación de metano."""
        total = 0.0
        k = self.k_decaimiento_anual
        for i, masa in enumerate(masas_anuales_ton):
            if i > anio_evaluacion:
                continue
            total += k * self.l0_m3_ch4_por_mg * masa * math.exp(-k * (anio_evaluacion - i))
        return total

    def proyeccion(
        self, masas_anuales_ton: List[float], anios_proyeccion: int = 20
    ) -> List[dict]:
        resultado = []
        for t in range(anios_proyeccion + 1):
            q_ch4 = self.generacion_metano_m3_anio(masas_anuales_ton, t)
            # Densidad aprox. del CH4 ≈ 0.68 kg/m3 (condiciones estándar)
            kg_ch4 = q_ch4 * 0.68
            co2eq_ton = (kg_ch4 * GWP_METANO) / 1000.0
            resultado.append({
                "anio": t,
                "m3_ch4_anio": round(q_ch4, 1),
                "co2eq_ton_anio": round(co2eq_ton, 2),
            })
        return resultado
