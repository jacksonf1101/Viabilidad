"""
Software de Viabilidad de Gestión de Residuos — MVP
========================================================
Módulo Técnico y Logístico:
  - Generación de residuos por zona
  - Capacidad de infraestructura (flota + plantas)
  - Optimización de rutas de recolección (CVRP) con mapa real

Ejecutar con:  python main.py
"""

import sys
import os
import tempfile

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QGroupBox, QFormLayout, QDoubleSpinBox,
    QSpinBox, QMessageBox, QHeaderView, QSplitter, QTextEdit,
    QCheckBox, QFileDialog
)
from PySide6.QtCore import Qt
from PySide6.QtWebEngineWidgets import QWebEngineView

from modules.generation import (
    ProyectoGeneracion, ZonaResidencial, ZonaComercial, ZonaIndustrial
)
from modules.capacity import FlotaYPlanta, Camion, PlantaTransferencia
from modules.routing import optimizar_rutas, PuntoRecoleccion
from modules.financial import ProyectoFinanciero, CostoOperativo, MaterialReciclable
from modules.environmental import (
    HuellaCarbono, MaterialEmisionEvitada, ParametrosLixiviado, ParametrosLandGEM,
    FACTORES_EMISION_DEFAULT,
)
from modules.social import (
    puntos_calor_generacion, puntos_calor_deficit_reciclaje,
    ranking_zonas_por_generacion, ranking_zonas_por_deficit_reciclaje,
)
from modules.persistence import guardar_proyecto, cargar_proyecto

import folium
from folium.plugins import HeatMap


# ---------------------------------------------------------------------
# PESTAÑA 1: Generación de Residuos
# ---------------------------------------------------------------------
class TabGeneracion(QWidget):
    def __init__(self):
        super().__init__()
        self.proyecto = ProyectoGeneracion("Proyecto sin nombre")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # --- Formulario de zona residencial ---
        grupo_res = QGroupBox("Agregar zona residencial")
        form_res = QFormLayout()
        self.res_nombre = QLineEdit()
        self.res_poblacion = QSpinBox()
        self.res_poblacion.setRange(0, 5_000_000)
        self.res_ppc = QDoubleSpinBox()
        self.res_ppc.setRange(0.1, 5.0)
        self.res_ppc.setSingleStep(0.05)
        self.res_ppc.setValue(0.9)
        self.res_ppc.setSuffix(" kg/hab/día")
        self.res_crecimiento = QDoubleSpinBox()
        self.res_crecimiento.setRange(0.0, 0.20)
        self.res_crecimiento.setSingleStep(0.005)
        self.res_crecimiento.setValue(0.02)
        self.res_crecimiento.setSuffix(" (tasa anual)")
        self.res_lat = QDoubleSpinBox()
        self.res_lat.setRange(-90, 90)
        self.res_lat.setDecimals(6)
        self.res_lon = QDoubleSpinBox()
        self.res_lon.setRange(-180, 180)
        self.res_lon.setDecimals(6)
        self.res_reciclaje = QDoubleSpinBox()
        self.res_reciclaje.setRange(0, 100)
        self.res_reciclaje.setSuffix(" % reciclaje actual (opcional)")
        btn_res = QPushButton("Agregar zona residencial")
        btn_res.clicked.connect(self._agregar_residencial)
        form_res.addRow("Nombre de la zona:", self.res_nombre)
        form_res.addRow("Población:", self.res_poblacion)
        form_res.addRow("Generación per cápita:", self.res_ppc)
        form_res.addRow("Crecimiento poblacional:", self.res_crecimiento)
        form_res.addRow("Latitud (mapa, opcional):", self.res_lat)
        form_res.addRow("Longitud (mapa, opcional):", self.res_lon)
        form_res.addRow("Tasa de reciclaje:", self.res_reciclaje)
        form_res.addRow(btn_res)
        grupo_res.setLayout(form_res)

        # --- Formulario de zona comercial ---
        grupo_com = QGroupBox("Agregar zona comercial")
        form_com = QFormLayout()
        self.com_nombre = QLineEdit()
        self.com_locales = QSpinBox()
        self.com_locales.setRange(0, 100_000)
        self.com_factor = QDoubleSpinBox()
        self.com_factor.setRange(0.1, 500)
        self.com_factor.setValue(15.0)
        self.com_factor.setSuffix(" kg/local/día")
        self.com_lat = QDoubleSpinBox()
        self.com_lat.setRange(-90, 90)
        self.com_lat.setDecimals(6)
        self.com_lon = QDoubleSpinBox()
        self.com_lon.setRange(-180, 180)
        self.com_lon.setDecimals(6)
        btn_com = QPushButton("Agregar zona comercial")
        btn_com.clicked.connect(self._agregar_comercial)
        form_com.addRow("Nombre de la zona:", self.com_nombre)
        form_com.addRow("Número de locales:", self.com_locales)
        form_com.addRow("Factor de generación:", self.com_factor)
        form_com.addRow("Latitud (mapa, opcional):", self.com_lat)
        form_com.addRow("Longitud (mapa, opcional):", self.com_lon)
        form_com.addRow(btn_com)
        grupo_com.setLayout(form_com)

        # --- Formulario de zona industrial ---
        grupo_ind = QGroupBox("Agregar zona industrial")
        form_ind = QFormLayout()
        self.ind_nombre = QLineEdit()
        self.ind_empleados = QSpinBox()
        self.ind_empleados.setRange(0, 200_000)
        self.ind_factor = QDoubleSpinBox()
        self.ind_factor.setRange(0.1, 100)
        self.ind_factor.setValue(2.5)
        self.ind_factor.setSuffix(" kg/empleado/día")
        self.ind_lat = QDoubleSpinBox()
        self.ind_lat.setRange(-90, 90)
        self.ind_lat.setDecimals(6)
        self.ind_lon = QDoubleSpinBox()
        self.ind_lon.setRange(-180, 180)
        self.ind_lon.setDecimals(6)
        btn_ind = QPushButton("Agregar zona industrial")
        btn_ind.clicked.connect(self._agregar_industrial)
        form_ind.addRow("Nombre de la zona:", self.ind_nombre)
        form_ind.addRow("Número de empleados:", self.ind_empleados)
        form_ind.addRow("Factor de generación:", self.ind_factor)
        form_ind.addRow("Latitud (mapa, opcional):", self.ind_lat)
        form_ind.addRow("Longitud (mapa, opcional):", self.ind_lon)
        form_ind.addRow(btn_ind)
        grupo_ind.setLayout(form_ind)

        forms_row = QHBoxLayout()
        forms_row.addWidget(grupo_res)
        forms_row.addWidget(grupo_com)
        forms_row.addWidget(grupo_ind)
        layout.addLayout(forms_row)

        # --- Tabla de zonas agregadas ---
        self.tabla_zonas = QTableWidget(0, 3)
        self.tabla_zonas.setHorizontalHeaderLabels(["Tipo", "Nombre", "Detalle"])
        self.tabla_zonas.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.tabla_zonas)

        # --- Resultado ---
        btn_calcular = QPushButton("Calcular generación total")
        btn_calcular.clicked.connect(self._calcular)
        layout.addWidget(btn_calcular)

        self.resultado_texto = QTextEdit()
        self.resultado_texto.setReadOnly(True)
        self.resultado_texto.setMaximumHeight(160)
        layout.addWidget(self.resultado_texto)

    def _agregar_residencial(self):
        if not self.res_nombre.text().strip():
            QMessageBox.warning(self, "Falta información", "Ingresa el nombre de la zona.")
            return
        zona = ZonaResidencial(
            nombre=self.res_nombre.text().strip(),
            poblacion=self.res_poblacion.value(),
            ppc_kg_hab_dia=self.res_ppc.value(),
            tasa_crecimiento_anual=self.res_crecimiento.value(),
            lat=self.res_lat.value(),
            lon=self.res_lon.value(),
            tasa_reciclaje_pct=self.res_reciclaje.value(),
        )
        self.proyecto.zonas_residenciales.append(zona)
        self._agregar_fila("Residencial", zona.nombre, f"{zona.poblacion} hab.")
        self.res_nombre.clear()

    def _agregar_comercial(self):
        if not self.com_nombre.text().strip():
            QMessageBox.warning(self, "Falta información", "Ingresa el nombre de la zona.")
            return
        zona = ZonaComercial(
            nombre=self.com_nombre.text().strip(),
            numero_locales=self.com_locales.value(),
            factor_kg_local_dia=self.com_factor.value(),
            lat=self.com_lat.value(),
            lon=self.com_lon.value(),
        )
        self.proyecto.zonas_comerciales.append(zona)
        self._agregar_fila("Comercial", zona.nombre, f"{zona.numero_locales} locales")
        self.com_nombre.clear()

    def _agregar_industrial(self):
        if not self.ind_nombre.text().strip():
            QMessageBox.warning(self, "Falta información", "Ingresa el nombre de la zona.")
            return
        zona = ZonaIndustrial(
            nombre=self.ind_nombre.text().strip(),
            numero_empleados=self.ind_empleados.value(),
            factor_kg_empleado_dia=self.ind_factor.value(),
            lat=self.ind_lat.value(),
            lon=self.ind_lon.value(),
        )
        self.proyecto.zonas_industriales.append(zona)
        self._agregar_fila("Industrial", zona.nombre, f"{zona.numero_empleados} empleados")
        self.ind_nombre.clear()

    def _agregar_fila(self, tipo, nombre, detalle):
        row = self.tabla_zonas.rowCount()
        self.tabla_zonas.insertRow(row)
        self.tabla_zonas.setItem(row, 0, QTableWidgetItem(tipo))
        self.tabla_zonas.setItem(row, 1, QTableWidgetItem(nombre))
        self.tabla_zonas.setItem(row, 2, QTableWidgetItem(detalle))

    def _calcular(self):
        if not (self.proyecto.zonas_residenciales or self.proyecto.zonas_comerciales
                or self.proyecto.zonas_industriales):
            QMessageBox.warning(self, "Sin datos", "Agrega al menos una zona antes de calcular.")
            return

        desglose = self.proyecto.desglose_por_fuente()
        total_dia = self.proyecto.total_diario_toneladas()
        total_mes = self.proyecto.total_mensual_toneladas()
        proyeccion = self.proyecto.proyeccion_multianual(5)

        texto = (
            f"GENERACIÓN TOTAL ACTUAL\n"
            f"  Residencial: {desglose['residencial_kg']:.1f} kg/día\n"
            f"  Comercial:   {desglose['comercial_kg']:.1f} kg/día\n"
            f"  Industrial:  {desglose['industrial_kg']:.1f} kg/día\n"
            f"  TOTAL: {total_dia:.2f} ton/día  |  {total_mes:.2f} ton/mes\n\n"
            f"PROYECCIÓN A 5 AÑOS:\n"
        )
        for p in proyeccion:
            texto += f"  Año {p['anio']}: {p['toneladas_dia']:.2f} ton/día\n"

        self.resultado_texto.setPlainText(texto)

    def volumen_actual_ton_dia(self) -> float:
        return self.proyecto.total_diario_toneladas()

    def volumen_actual_ton_mes(self) -> float:
        return self.proyecto.total_mensual_toneladas()

    # --- Persistencia ---
    def get_state(self) -> dict:
        from dataclasses import asdict
        return {
            "nombre_proyecto": self.proyecto.nombre_proyecto,
            "zonas_residenciales": [asdict(z) for z in self.proyecto.zonas_residenciales],
            "zonas_comerciales": [asdict(z) for z in self.proyecto.zonas_comerciales],
            "zonas_industriales": [asdict(z) for z in self.proyecto.zonas_industriales],
        }

    def load_state(self, estado: dict) -> None:
        self.proyecto = ProyectoGeneracion(estado.get("nombre_proyecto", "Proyecto sin nombre"))
        self.tabla_zonas.setRowCount(0)
        for d in estado.get("zonas_residenciales", []):
            z = ZonaResidencial(**d)
            self.proyecto.zonas_residenciales.append(z)
            self._agregar_fila("Residencial", z.nombre, f"{z.poblacion} hab.")
        for d in estado.get("zonas_comerciales", []):
            z = ZonaComercial(**d)
            self.proyecto.zonas_comerciales.append(z)
            self._agregar_fila("Comercial", z.nombre, f"{z.numero_locales} locales")
        for d in estado.get("zonas_industriales", []):
            z = ZonaIndustrial(**d)
            self.proyecto.zonas_industriales.append(z)
            self._agregar_fila("Industrial", z.nombre, f"{z.numero_empleados} empleados")
        if (self.proyecto.zonas_residenciales or self.proyecto.zonas_comerciales
                or self.proyecto.zonas_industriales):
            self._calcular()


# ---------------------------------------------------------------------
# PESTAÑA 2: Capacidad de Infraestructura
# ---------------------------------------------------------------------
class TabCapacidad(QWidget):
    def __init__(self, tab_generacion: TabGeneracion):
        super().__init__()
        self.tab_generacion = tab_generacion
        self.flota = FlotaYPlanta()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        grupo_camion = QGroupBox("Agregar camión a la flota")
        form_c = QFormLayout()
        self.cam_id = QLineEdit()
        self.cam_capacidad = QDoubleSpinBox()
        self.cam_capacidad.setRange(0.5, 30)
        self.cam_capacidad.setValue(8.0)
        self.cam_capacidad.setSuffix(" ton/viaje")
        self.cam_viajes = QSpinBox()
        self.cam_viajes.setRange(1, 6)
        self.cam_viajes.setValue(2)
        self.cam_disponibilidad = QDoubleSpinBox()
        self.cam_disponibilidad.setRange(0.1, 1.0)
        self.cam_disponibilidad.setSingleStep(0.05)
        self.cam_disponibilidad.setValue(0.9)
        btn_cam = QPushButton("Agregar camión")
        btn_cam.clicked.connect(self._agregar_camion)
        form_c.addRow("Identificador:", self.cam_id)
        form_c.addRow("Capacidad por viaje:", self.cam_capacidad)
        form_c.addRow("Viajes por día:", self.cam_viajes)
        form_c.addRow("Disponibilidad (0-1):", self.cam_disponibilidad)
        form_c.addRow(btn_cam)
        grupo_camion.setLayout(form_c)

        grupo_planta = QGroupBox("Agregar planta de transferencia/disposición")
        form_p = QFormLayout()
        self.plt_nombre = QLineEdit()
        self.plt_capacidad = QDoubleSpinBox()
        self.plt_capacidad.setRange(1, 5000)
        self.plt_capacidad.setValue(40)
        self.plt_capacidad.setSuffix(" ton/día")
        btn_plt = QPushButton("Agregar planta")
        btn_plt.clicked.connect(self._agregar_planta)
        form_p.addRow("Nombre:", self.plt_nombre)
        form_p.addRow("Capacidad diaria:", self.plt_capacidad)
        form_p.addRow(btn_plt)
        grupo_planta.setLayout(form_p)

        row = QHBoxLayout()
        row.addWidget(grupo_camion)
        row.addWidget(grupo_planta)
        layout.addLayout(row)

        self.tabla_infra = QTableWidget(0, 3)
        self.tabla_infra.setHorizontalHeaderLabels(["Tipo", "Nombre/ID", "Capacidad"])
        self.tabla_infra.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.tabla_infra)

        btn_eval = QPushButton("Evaluar capacidad vs. generación proyectada (pestaña 1)")
        btn_eval.clicked.connect(self._evaluar)
        layout.addWidget(btn_eval)

        self.resultado_texto = QTextEdit()
        self.resultado_texto.setReadOnly(True)
        self.resultado_texto.setMaximumHeight(200)
        layout.addWidget(self.resultado_texto)

    def _agregar_camion(self):
        if not self.cam_id.text().strip():
            QMessageBox.warning(self, "Falta información", "Ingresa el identificador del camión.")
            return
        c = Camion(
            identificador=self.cam_id.text().strip(),
            capacidad_toneladas=self.cam_capacidad.value(),
            viajes_dia=self.cam_viajes.value(),
            disponibilidad_pct=self.cam_disponibilidad.value(),
        )
        self.flota.camiones.append(c)
        row = self.tabla_infra.rowCount()
        self.tabla_infra.insertRow(row)
        self.tabla_infra.setItem(row, 0, QTableWidgetItem("Camión"))
        self.tabla_infra.setItem(row, 1, QTableWidgetItem(c.identificador))
        self.tabla_infra.setItem(
            row, 2, QTableWidgetItem(f"{c.capacidad_diaria_toneladas():.2f} ton/día")
        )
        self.cam_id.clear()

    def _agregar_planta(self):
        if not self.plt_nombre.text().strip():
            QMessageBox.warning(self, "Falta información", "Ingresa el nombre de la planta.")
            return
        p = PlantaTransferencia(
            nombre=self.plt_nombre.text().strip(),
            capacidad_diaria_toneladas=self.plt_capacidad.value(),
        )
        self.flota.plantas.append(p)
        row = self.tabla_infra.rowCount()
        self.tabla_infra.insertRow(row)
        self.tabla_infra.setItem(row, 0, QTableWidgetItem("Planta"))
        self.tabla_infra.setItem(row, 1, QTableWidgetItem(p.nombre))
        self.tabla_infra.setItem(
            row, 2, QTableWidgetItem(f"{p.capacidad_diaria_toneladas:.2f} ton/día")
        )
        self.plt_nombre.clear()

    def _evaluar(self):
        volumen = self.tab_generacion.volumen_actual_ton_dia()
        if volumen <= 0:
            QMessageBox.warning(
                self, "Sin generación calculada",
                "Ve a la pestaña 'Generación' y calcula el volumen proyectado primero."
            )
            return
        if not self.flota.camiones:
            QMessageBox.warning(self, "Sin flota", "Agrega al menos un camión.")
            return

        r = self.flota.evaluar(volumen)
        icono = {"OK": "✅", "ALERTA": "⚠️", "CRÍTICO": "🔴", "SIN DATOS": "❔"}
        texto = (
            f"Volumen proyectado: {r['volumen_proyectado_ton_dia']} ton/día\n\n"
            f"FLOTA:\n"
            f"  Capacidad total: {r['capacidad_flota_ton_dia']} ton/día\n"
            f"  Utilización: {r['utilizacion_flota_pct']}%  "
            f"{icono.get(r['estado_flota'],'')} {r['estado_flota']}\n"
            f"  Déficit: {r['deficit_flota_ton_dia']} ton/día\n"
        )
        if r["camiones_adicionales_sugeridos"]:
            texto += f"  → Camiones adicionales sugeridos: {r['camiones_adicionales_sugeridos']}\n"
        texto += (
            f"\nPLANTA(S):\n"
            f"  Capacidad total: {r['capacidad_plantas_ton_dia']} ton/día\n"
            f"  Utilización: {r['utilizacion_planta_pct']}%  "
            f"{icono.get(r['estado_planta'],'')} {r['estado_planta']}\n"
        )
        self.resultado_texto.setPlainText(texto)

    # --- Persistencia ---
    def get_state(self) -> dict:
        from dataclasses import asdict
        return {
            "camiones": [asdict(c) for c in self.flota.camiones],
            "plantas": [asdict(p) for p in self.flota.plantas],
        }

    def load_state(self, estado: dict) -> None:
        self.flota = FlotaYPlanta()
        self.tabla_infra.setRowCount(0)
        for d in estado.get("camiones", []):
            c = Camion(**d)
            self.flota.camiones.append(c)
            row = self.tabla_infra.rowCount()
            self.tabla_infra.insertRow(row)
            self.tabla_infra.setItem(row, 0, QTableWidgetItem("Camión"))
            self.tabla_infra.setItem(row, 1, QTableWidgetItem(c.identificador))
            self.tabla_infra.setItem(
                row, 2, QTableWidgetItem(f"{c.capacidad_diaria_toneladas():.2f} ton/día")
            )
        for d in estado.get("plantas", []):
            p = PlantaTransferencia(**d)
            self.flota.plantas.append(p)
            row = self.tabla_infra.rowCount()
            self.tabla_infra.insertRow(row)
            self.tabla_infra.setItem(row, 0, QTableWidgetItem("Planta"))
            self.tabla_infra.setItem(row, 1, QTableWidgetItem(p.nombre))
            self.tabla_infra.setItem(
                row, 2, QTableWidgetItem(f"{p.capacidad_diaria_toneladas:.2f} ton/día")
            )


# ---------------------------------------------------------------------
# PESTAÑA 3: Optimización de Rutas
# ---------------------------------------------------------------------
class TabRutas(QWidget):
    def __init__(self):
        super().__init__()
        self.puntos = []  # PuntoRecoleccion, [0] = depósito
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)

        # --- Panel izquierdo: formularios y tabla ---
        panel_izq = QVBoxLayout()

        grupo_dep = QGroupBox("Depósito / Planta base (punto de partida)")
        form_dep = QFormLayout()
        self.dep_nombre = QLineEdit("Depósito")
        self.dep_lat = QDoubleSpinBox()
        self.dep_lat.setRange(-90, 90)
        self.dep_lat.setDecimals(6)
        self.dep_lat.setValue(18.4655)
        self.dep_lon = QDoubleSpinBox()
        self.dep_lon.setRange(-180, 180)
        self.dep_lon.setDecimals(6)
        self.dep_lon.setValue(-69.8977)
        btn_dep = QPushButton("Fijar depósito")
        btn_dep.clicked.connect(self._fijar_deposito)
        self.label_estado_deposito = QLabel("⚠️ Depósito no fijado todavía")
        form_dep.addRow("Nombre:", self.dep_nombre)
        form_dep.addRow("Latitud:", self.dep_lat)
        form_dep.addRow("Longitud:", self.dep_lon)
        form_dep.addRow(btn_dep)
        form_dep.addRow(self.label_estado_deposito)
        grupo_dep.setLayout(form_dep)
        panel_izq.addWidget(grupo_dep)

        grupo_punto = QGroupBox("Agregar punto de recolección")
        form_pt = QFormLayout()
        self.pt_nombre = QLineEdit()
        self.pt_lat = QDoubleSpinBox()
        self.pt_lat.setRange(-90, 90)
        self.pt_lat.setDecimals(6)
        self.pt_lon = QDoubleSpinBox()
        self.pt_lon.setRange(-180, 180)
        self.pt_lon.setDecimals(6)
        self.pt_demanda = QDoubleSpinBox()
        self.pt_demanda.setRange(1, 50000)
        self.pt_demanda.setValue(500)
        self.pt_demanda.setSuffix(" kg")
        btn_pt = QPushButton("Agregar punto")
        btn_pt.clicked.connect(self._agregar_punto)
        form_pt.addRow("Nombre:", self.pt_nombre)
        form_pt.addRow("Latitud:", self.pt_lat)
        form_pt.addRow("Longitud:", self.pt_lon)
        form_pt.addRow("Demanda:", self.pt_demanda)
        form_pt.addRow(btn_pt)
        grupo_punto.setLayout(form_pt)
        panel_izq.addWidget(grupo_punto)

        grupo_flota = QGroupBox("Flota disponible para esta ruta")
        form_f = QFormLayout()
        self.num_camiones = QSpinBox()
        self.num_camiones.setRange(1, 50)
        self.num_camiones.setValue(2)
        self.cap_camion = QDoubleSpinBox()
        self.cap_camion.setRange(100, 30000)
        self.cap_camion.setValue(1500)
        self.cap_camion.setSuffix(" kg")
        self.usar_osrm = QCheckBox("Usar rutas reales por calle (OSRM, requiere internet)")
        self.usar_osrm.setChecked(True)
        form_f.addRow("Número de camiones:", self.num_camiones)
        form_f.addRow("Capacidad por camión:", self.cap_camion)
        form_f.addRow(self.usar_osrm)
        grupo_flota.setLayout(form_f)
        panel_izq.addWidget(grupo_flota)

        self.tabla_puntos = QTableWidget(0, 4)
        self.tabla_puntos.setHorizontalHeaderLabels(["Nombre", "Lat", "Lon", "Demanda (kg)"])
        self.tabla_puntos.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        panel_izq.addWidget(self.tabla_puntos)

        btn_optimizar = QPushButton("Optimizar rutas")
        btn_optimizar.clicked.connect(self._optimizar)
        panel_izq.addWidget(btn_optimizar)

        self.resultado_texto = QTextEdit()
        self.resultado_texto.setReadOnly(True)
        self.resultado_texto.setMaximumHeight(160)
        panel_izq.addWidget(self.resultado_texto)

        panel_izq_widget = QWidget()
        panel_izq_widget.setLayout(panel_izq)

        # --- Panel derecho: mapa ---
        self.mapa_view = QWebEngineView()
        self._render_mapa_vacio()

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(panel_izq_widget)
        splitter.addWidget(self.mapa_view)
        splitter.setSizes([480, 600])
        layout.addWidget(splitter)

    def _render_mapa_vacio(self):
        m = folium.Map(location=[18.4655, -69.8977], zoom_start=11)
        self._mostrar_mapa(m)

    def _mostrar_mapa(self, mapa: folium.Map):
        tmp_path = os.path.join(tempfile.gettempdir(), "mapa_rutas.html")
        mapa.save(tmp_path)
        self.mapa_view.load(f"file://{tmp_path}")

    def _fijar_deposito(self):
        deposito = PuntoRecoleccion(
            nombre=self.dep_nombre.text().strip() or "Depósito",
            lat=self.dep_lat.value(),
            lon=self.dep_lon.value(),
            demanda_kg=0,
        )
        if self.puntos:
            self.puntos[0] = deposito  # reemplaza el depósito existente, conserva los demás puntos
        else:
            self.puntos.append(deposito)
        self.label_estado_deposito.setText(f"✅ Depósito activo: {deposito.nombre}")

    def _agregar_punto(self):
        if not self.puntos:
            QMessageBox.warning(self, "Falta el depósito", "Primero fija el depósito.")
            return
        if not self.pt_nombre.text().strip():
            QMessageBox.warning(self, "Falta información", "Ingresa el nombre del punto.")
            return
        p = PuntoRecoleccion(
            nombre=self.pt_nombre.text().strip(),
            lat=self.pt_lat.value(),
            lon=self.pt_lon.value(),
            demanda_kg=self.pt_demanda.value(),
        )
        self.puntos.append(p)
        row = self.tabla_puntos.rowCount()
        self.tabla_puntos.insertRow(row)
        self.tabla_puntos.setItem(row, 0, QTableWidgetItem(p.nombre))
        self.tabla_puntos.setItem(row, 1, QTableWidgetItem(str(p.lat)))
        self.tabla_puntos.setItem(row, 2, QTableWidgetItem(str(p.lon)))
        self.tabla_puntos.setItem(row, 3, QTableWidgetItem(str(p.demanda_kg)))
        self.pt_nombre.clear()

    def _optimizar(self):
        if not self.puntos or len(self.puntos) < 2:
            QMessageBox.warning(
                self, "Datos insuficientes",
                "Fija el depósito y agrega al menos un punto de recolección."
            )
            return

        capacidades = [self.cap_camion.value()] * self.num_camiones.value()
        try:
            resultado = optimizar_rutas(
                self.puntos, capacidades, usar_osrm=self.usar_osrm.isChecked()
            )
        except Exception as e:
            QMessageBox.critical(self, "Error de optimización", str(e))
            return

        texto = f"Fuente de distancias: {resultado.fuente_distancias}\n\n"
        colores = ["red", "blue", "green", "purple", "orange", "darkred", "cadetblue"]
        m = folium.Map(location=[self.puntos[0].lat, self.puntos[0].lon], zoom_start=12)
        folium.Marker(
            [self.puntos[0].lat, self.puntos[0].lon],
            popup=self.puntos[0].nombre,
            icon=folium.Icon(color="black", icon="home"),
        ).add_to(m)

        nombre_a_punto = {p.nombre: p for p in self.puntos}

        for i, ruta in enumerate(resultado.rutas):
            color = colores[i % len(colores)]
            coords = []
            for nombre in ruta.secuencia_puntos:
                p = nombre_a_punto[nombre]
                coords.append((p.lat, p.lon))
                if nombre != self.puntos[0].nombre:
                    folium.Marker(
                        [p.lat, p.lon],
                        popup=f"{p.nombre} ({p.demanda_kg} kg) — {ruta.vehiculo}",
                        icon=folium.Icon(color=color),
                    ).add_to(m)
            folium.PolyLine(coords, color=color, weight=4, opacity=0.8,
                             tooltip=ruta.vehiculo).add_to(m)

            texto += (
                f"{ruta.vehiculo}: {' → '.join(ruta.secuencia_puntos)}\n"
                f"   Distancia: {ruta.distancia_total_km} km | "
                f"Duración estimada: {ruta.duracion_total_min} min | "
                f"Carga: {ruta.carga_total_kg} kg\n\n"
            )

        texto += f"Distancia total de la flota: {resultado.distancia_total_flota_km} km\n"
        if resultado.puntos_sin_asignar:
            texto += (
                f"⚠️ Puntos SIN asignar (capacidad insuficiente): "
                f"{', '.join(resultado.puntos_sin_asignar)}\n"
            )

        self.resultado_texto.setPlainText(texto)
        self._mostrar_mapa(m)

    # --- Persistencia ---
    def get_state(self) -> dict:
        from dataclasses import asdict
        return {
            "puntos": [asdict(p) for p in self.puntos],
            "num_camiones": self.num_camiones.value(),
            "cap_camion": self.cap_camion.value(),
            "usar_osrm": self.usar_osrm.isChecked(),
        }

    def load_state(self, estado: dict) -> None:
        self.puntos = []
        self.tabla_puntos.setRowCount(0)
        puntos_guardados = estado.get("puntos", [])
        if puntos_guardados:
            deposito_d = puntos_guardados[0]
            self.dep_nombre.setText(deposito_d["nombre"])
            self.dep_lat.setValue(deposito_d["lat"])
            self.dep_lon.setValue(deposito_d["lon"])
            self.puntos.append(PuntoRecoleccion(**deposito_d))
            self.label_estado_deposito.setText(f"✅ Depósito activo: {deposito_d['nombre']}")
            for d in puntos_guardados[1:]:
                p = PuntoRecoleccion(**d)
                self.puntos.append(p)
                row = self.tabla_puntos.rowCount()
                self.tabla_puntos.insertRow(row)
                self.tabla_puntos.setItem(row, 0, QTableWidgetItem(p.nombre))
                self.tabla_puntos.setItem(row, 1, QTableWidgetItem(str(p.lat)))
                self.tabla_puntos.setItem(row, 2, QTableWidgetItem(str(p.lon)))
                self.tabla_puntos.setItem(row, 3, QTableWidgetItem(str(p.demanda_kg)))
        self.num_camiones.setValue(estado.get("num_camiones", 2))
        self.cap_camion.setValue(estado.get("cap_camion", 1500))
        self.usar_osrm.setChecked(estado.get("usar_osrm", True))


# ---------------------------------------------------------------------
# PESTAÑA 4: Económico y Financiero
# ---------------------------------------------------------------------
class TabFinanciero(QWidget):
    def __init__(self, tab_generacion: TabGeneracion):
        super().__init__()
        self.tab_generacion = tab_generacion
        self.proyecto_fin = ProyectoFinanciero("Proyecto sin nombre")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        forms_row = QHBoxLayout()

        # --- Costos operativos ---
        grupo_costos = QGroupBox("Costos operativos mensuales")
        form_costos = QFormLayout()
        self.costo_concepto = QLineEdit()
        self.costo_monto = QDoubleSpinBox()
        self.costo_monto.setRange(0, 100_000_000)
        self.costo_monto.setDecimals(2)
        self.costo_monto.setSuffix(" /mes")
        btn_costo = QPushButton("Agregar costo (ej. Combustible, Mano de obra...)")
        btn_costo.clicked.connect(self._agregar_costo)
        form_costos.addRow("Concepto:", self.costo_concepto)
        form_costos.addRow("Monto mensual:", self.costo_monto)
        form_costos.addRow(btn_costo)
        grupo_costos.setLayout(form_costos)

        # --- Materiales reciclables ---
        grupo_mat = QGroupBox("Ingresos por materiales reciclables")
        form_mat = QFormLayout()
        self.mat_nombre = QLineEdit()
        self.mat_porcentaje = QDoubleSpinBox()
        self.mat_porcentaje.setRange(0, 100)
        self.mat_porcentaje.setSuffix(" % del total de residuos")
        self.mat_precio = QDoubleSpinBox()
        self.mat_precio.setRange(0, 1000)
        self.mat_precio.setDecimals(2)
        self.mat_precio.setSuffix(" /kg")
        btn_mat = QPushButton("Agregar material (ej. Plástico, Cartón...)")
        btn_mat.clicked.connect(self._agregar_material)
        form_mat.addRow("Material:", self.mat_nombre)
        form_mat.addRow("% recuperable del total:", self.mat_porcentaje)
        form_mat.addRow("Precio de venta:", self.mat_precio)
        form_mat.addRow(btn_mat)
        grupo_mat.setLayout(form_mat)

        forms_row.addWidget(grupo_costos)
        forms_row.addWidget(grupo_mat)
        layout.addLayout(forms_row)

        self.tabla_fin = QTableWidget(0, 3)
        self.tabla_fin.setHorizontalHeaderLabels(["Tipo", "Concepto/Material", "Valor"])
        self.tabla_fin.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.tabla_fin)

        # --- Biogás, tarifa, inversión ---
        grupo_extra = QGroupBox("Biogás, tarifa e inversión")
        form_extra = QFormLayout()
        self.biogas = QDoubleSpinBox()
        self.biogas.setRange(0, 50_000_000)
        self.biogas.setDecimals(2)
        self.biogas.setSuffix(" /mes")
        self.num_usuarios = QSpinBox()
        self.num_usuarios.setRange(0, 5_000_000)
        self.tarifa = QDoubleSpinBox()
        self.tarifa.setRange(0, 100_000)
        self.tarifa.setDecimals(2)
        self.tarifa.setSuffix(" /usuario/mes")
        btn_tarifa_eq = QPushButton("Calcular tarifa de equilibrio y aplicarla")
        btn_tarifa_eq.clicked.connect(self._calcular_tarifa_equilibrio)
        self.inversion = QDoubleSpinBox()
        self.inversion.setRange(0, 1_000_000_000)
        self.inversion.setDecimals(2)
        form_extra.addRow("Ingreso por biogás:", self.biogas)
        form_extra.addRow("Número de usuarios (hogares/empresas):", self.num_usuarios)
        form_extra.addRow("Tarifa mensual por usuario:", self.tarifa)
        form_extra.addRow(btn_tarifa_eq)
        form_extra.addRow("Inversión inicial (camiones/planta):", self.inversion)
        grupo_extra.setLayout(form_extra)
        layout.addWidget(grupo_extra)

        btn_calcular = QPushButton("Calcular viabilidad económica")
        btn_calcular.clicked.connect(self._calcular)
        layout.addWidget(btn_calcular)

        self.resultado_texto = QTextEdit()
        self.resultado_texto.setReadOnly(True)
        self.resultado_texto.setMaximumHeight(200)
        layout.addWidget(self.resultado_texto)

    def _agregar_costo(self):
        if not self.costo_concepto.text().strip():
            QMessageBox.warning(self, "Falta información", "Ingresa el concepto del costo.")
            return
        c = CostoOperativo(self.costo_concepto.text().strip(), self.costo_monto.value())
        self.proyecto_fin.costos_operativos.append(c)
        row = self.tabla_fin.rowCount()
        self.tabla_fin.insertRow(row)
        self.tabla_fin.setItem(row, 0, QTableWidgetItem("Costo"))
        self.tabla_fin.setItem(row, 1, QTableWidgetItem(c.concepto))
        self.tabla_fin.setItem(row, 2, QTableWidgetItem(f"{c.monto_mensual:.2f} /mes"))
        self.costo_concepto.clear()

    def _agregar_material(self):
        if not self.mat_nombre.text().strip():
            QMessageBox.warning(self, "Falta información", "Ingresa el nombre del material.")
            return
        m = MaterialReciclable(
            self.mat_nombre.text().strip(), self.mat_porcentaje.value(), self.mat_precio.value()
        )
        self.proyecto_fin.materiales_reciclables.append(m)
        row = self.tabla_fin.rowCount()
        self.tabla_fin.insertRow(row)
        self.tabla_fin.setItem(row, 0, QTableWidgetItem("Reciclable"))
        self.tabla_fin.setItem(row, 1, QTableWidgetItem(m.nombre))
        self.tabla_fin.setItem(
            row, 2, QTableWidgetItem(f"{m.porcentaje_del_total}% @ {m.precio_venta_kg}/kg")
        )
        self.mat_nombre.clear()

    def _sync_inputs_a_proyecto(self):
        self.proyecto_fin.ingreso_biogas_mensual = self.biogas.value()
        self.proyecto_fin.numero_usuarios = self.num_usuarios.value()
        self.proyecto_fin.tarifa_mensual_por_usuario = self.tarifa.value()
        self.proyecto_fin.inversion_inicial = self.inversion.value()

    def _volumen_ton_mes(self) -> float:
        return self.tab_generacion.proyecto.total_mensual_toneladas()

    def _calcular_tarifa_equilibrio(self):
        if not self.proyecto_fin.costos_operativos:
            QMessageBox.warning(self, "Sin costos", "Agrega al menos un costo operativo.")
            return
        self._sync_inputs_a_proyecto()
        toneladas_mes = self._volumen_ton_mes()
        if toneladas_mes <= 0:
            QMessageBox.warning(
                self, "Sin generación calculada",
                "Ve a la pestaña 'Generación' y calcula el volumen proyectado primero."
            )
            return
        tarifa_eq = self.proyecto_fin.tarifa_equilibrio_por_usuario(toneladas_mes)
        if tarifa_eq is None:
            QMessageBox.warning(self, "Sin usuarios", "Ingresa el número de usuarios primero.")
            return
        self.tarifa.setValue(tarifa_eq)
        self.resultado_texto.setPlainText(
            f"Tarifa de equilibrio calculada y aplicada: {tarifa_eq:.2f} /usuario/mes\n"
            f"Presiona 'Calcular viabilidad económica' para ver el análisis completo."
        )

    def _calcular(self):
        if not self.proyecto_fin.costos_operativos:
            QMessageBox.warning(self, "Sin costos", "Agrega al menos un costo operativo.")
            return
        self._sync_inputs_a_proyecto()
        toneladas_mes = self._volumen_ton_mes()
        if toneladas_mes <= 0:
            QMessageBox.warning(
                self, "Sin generación calculada",
                "Ve a la pestaña 'Generación' y calcula el volumen proyectado primero."
            )
            return

        r = self.proyecto_fin.resumen(toneladas_mes)
        estado_balance = "SUPERAVIT ✅" if r["balance_mensual"] >= 0 else "DÉFICIT 🔴"

        texto = (
            f"Volumen procesado: {toneladas_mes:.2f} ton/mes\n\n"
            f"COSTOS:\n"
            f"  Costos operativos totales: {r['costos_totales_mensuales']:.2f} /mes\n"
            f"  Costo por tonelada: {r['costo_por_tonelada']:.2f} /ton\n\n"
            f"INGRESOS:\n"
            f"  Reciclables: {r['ingresos_reciclables_mensuales']:.2f} /mes\n"
            f"  Biogás: {r['ingreso_biogas_mensual']:.2f} /mes\n"
            f"  Tarifas ({self.num_usuarios.value()} usuarios x "
            f"{self.tarifa.value():.2f}): {r['recaudo_tarifas_mensual']:.2f} /mes\n"
            f"  TOTAL: {r['ingresos_totales_mensuales']:.2f} /mes\n\n"
            f"BALANCE MENSUAL: {r['balance_mensual']:.2f}  ({estado_balance})\n\n"
        )
        if r["tarifa_equilibrio_por_usuario"] is not None:
            texto += (
                f"Tarifa de equilibrio (autosostenible, sin margen): "
                f"{r['tarifa_equilibrio_por_usuario']:.2f} /usuario/mes\n\n"
            )
        if self.inversion.value() > 0:
            if r["roi_anios"] is not None:
                texto += (
                    f"RETORNO DE INVERSIÓN (ROI): {r['roi_anios']:.2f} años "
                    f"(inversión: {self.inversion.value():.2f})\n"
                )
            else:
                texto += (
                    "RETORNO DE INVERSIÓN: el balance mensual actual no es positivo — "
                    "la inversión no se recupera con estos parámetros. Ajusta la tarifa, "
                    "los ingresos por reciclaje o reduce costos.\n"
                )

        self.resultado_texto.setPlainText(texto)

    # --- Persistencia ---
    def get_state(self) -> dict:
        from dataclasses import asdict
        return {
            "costos_operativos": [asdict(c) for c in self.proyecto_fin.costos_operativos],
            "materiales_reciclables": [asdict(m) for m in self.proyecto_fin.materiales_reciclables],
            "biogas": self.biogas.value(),
            "num_usuarios": self.num_usuarios.value(),
            "tarifa": self.tarifa.value(),
            "inversion": self.inversion.value(),
        }

    def load_state(self, estado: dict) -> None:
        self.proyecto_fin = ProyectoFinanciero("Proyecto sin nombre")
        self.tabla_fin.setRowCount(0)
        for d in estado.get("costos_operativos", []):
            c = CostoOperativo(**d)
            self.proyecto_fin.costos_operativos.append(c)
            row = self.tabla_fin.rowCount()
            self.tabla_fin.insertRow(row)
            self.tabla_fin.setItem(row, 0, QTableWidgetItem("Costo"))
            self.tabla_fin.setItem(row, 1, QTableWidgetItem(c.concepto))
            self.tabla_fin.setItem(row, 2, QTableWidgetItem(f"{c.monto_mensual:.2f} /mes"))
        for d in estado.get("materiales_reciclables", []):
            m = MaterialReciclable(**d)
            self.proyecto_fin.materiales_reciclables.append(m)
            row = self.tabla_fin.rowCount()
            self.tabla_fin.insertRow(row)
            self.tabla_fin.setItem(row, 0, QTableWidgetItem("Reciclable"))
            self.tabla_fin.setItem(row, 1, QTableWidgetItem(m.nombre))
            self.tabla_fin.setItem(
                row, 2, QTableWidgetItem(f"{m.porcentaje_del_total}% @ {m.precio_venta_kg}/kg")
            )
        self.biogas.setValue(estado.get("biogas", 0.0))
        self.num_usuarios.setValue(estado.get("num_usuarios", 0))
        self.tarifa.setValue(estado.get("tarifa", 0.0))
        self.inversion.setValue(estado.get("inversion", 0.0))


# ---------------------------------------------------------------------
# PESTAÑA 5: Ambiental
# ---------------------------------------------------------------------
class TabAmbiental(QWidget):
    def __init__(self, tab_generacion: TabGeneracion, tab_rutas: TabRutas):
        super().__init__()
        self.tab_generacion = tab_generacion
        self.tab_rutas = tab_rutas
        self.huella = HuellaCarbono()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # --- Huella de carbono: reciclaje ---
        grupo_reciclaje = QGroupBox("CO₂ evitado por reciclaje")
        form_rec = QFormLayout()
        self.mat_nombre = QLineEdit()
        self.mat_kg_mes = QDoubleSpinBox()
        self.mat_kg_mes.setRange(0, 10_000_000)
        self.mat_kg_mes.setSuffix(" kg/mes reciclados")
        self.mat_factor = QDoubleSpinBox()
        self.mat_factor.setRange(0, 20)
        self.mat_factor.setDecimals(2)
        self.mat_factor.setValue(1.6)
        self.mat_factor.setSuffix(" kg CO₂eq evitado / kg")
        btn_factor_ref = QPushButton("Usar factores de referencia típicos")
        btn_factor_ref.clicked.connect(self._mostrar_factores_referencia)
        btn_mat = QPushButton("Agregar material")
        btn_mat.clicked.connect(self._agregar_material)
        form_rec.addRow("Material:", self.mat_nombre)
        form_rec.addRow("Cantidad reciclada:", self.mat_kg_mes)
        form_rec.addRow("Factor de emisión evitada:", self.mat_factor)
        form_rec.addRow(btn_factor_ref)
        form_rec.addRow(btn_mat)
        grupo_reciclaje.setLayout(form_rec)

        # --- Huella de carbono: rutas ---
        grupo_rutas = QGroupBox("CO₂ evitado por optimización de rutas")
        form_rutas = QFormLayout()
        self.dist_sin_optimizar = QDoubleSpinBox()
        self.dist_sin_optimizar.setRange(0, 5000)
        self.dist_sin_optimizar.setSuffix(" km/día (antes de optimizar)")
        self.dist_optimizada = QDoubleSpinBox()
        self.dist_optimizada.setRange(0, 5000)
        self.dist_optimizada.setSuffix(" km/día (optimizada)")
        btn_usar_ruta = QPushButton("Usar distancia optimizada calculada en pestaña 'Rutas'")
        btn_usar_ruta.clicked.connect(self._usar_distancia_rutas)
        self.consumo_diesel = QDoubleSpinBox()
        self.consumo_diesel.setRange(0.05, 2.0)
        self.consumo_diesel.setDecimals(2)
        self.consumo_diesel.setValue(0.35)
        self.consumo_diesel.setSuffix(" L diésel/km")
        form_rutas.addRow("Distancia sin optimizar:", self.dist_sin_optimizar)
        form_rutas.addRow("Distancia optimizada:", self.dist_optimizada)
        form_rutas.addRow(btn_usar_ruta)
        form_rutas.addRow("Consumo del camión:", self.consumo_diesel)
        grupo_rutas.setLayout(form_rutas)

        fila1 = QHBoxLayout()
        fila1.addWidget(grupo_reciclaje)
        fila1.addWidget(grupo_rutas)
        layout.addLayout(fila1)

        self.tabla_ambiental = QTableWidget(0, 3)
        self.tabla_ambiental.setHorizontalHeaderLabels(["Tipo", "Material", "Detalle"])
        self.tabla_ambiental.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla_ambiental.setMaximumHeight(120)
        layout.addWidget(self.tabla_ambiental)

        btn_huella = QPushButton("Calcular huella de carbono")
        btn_huella.clicked.connect(self._calcular_huella)
        layout.addWidget(btn_huella)

        self.resultado_huella = QTextEdit()
        self.resultado_huella.setReadOnly(True)
        self.resultado_huella.setMaximumHeight(140)
        layout.addWidget(self.resultado_huella)

        # --- Lixiviados y gases ---
        grupo_relleno = QGroupBox("Lixiviados y gases de relleno sanitario")
        form_relleno = QFormLayout()
        self.area_relleno = QDoubleSpinBox()
        self.area_relleno.setRange(100, 10_000_000)
        self.area_relleno.setValue(50000)
        self.area_relleno.setSuffix(" m²")
        self.precipitacion = QDoubleSpinBox()
        self.precipitacion.setRange(0, 5000)
        self.precipitacion.setValue(1400)
        self.precipitacion.setSuffix(" mm/año")
        self.coef_infiltracion = QDoubleSpinBox()
        self.coef_infiltracion.setRange(1, 100)
        self.coef_infiltracion.setValue(20)
        self.coef_infiltracion.setSuffix(" % infiltración → lixiviado")
        self.k_landgem = QDoubleSpinBox()
        self.k_landgem.setRange(0.001, 1.0)
        self.k_landgem.setDecimals(3)
        self.k_landgem.setValue(0.05)
        self.k_landgem.setSuffix(" k (1/año, decaimiento)")
        self.l0_landgem = QDoubleSpinBox()
        self.l0_landgem.setRange(10, 300)
        self.l0_landgem.setValue(100)
        self.l0_landgem.setSuffix(" L0 (m³ CH₄/ton)")
        self.anios_vida_util = QSpinBox()
        self.anios_vida_util.setRange(1, 50)
        self.anios_vida_util.setValue(15)
        self.anio_evaluar = QSpinBox()
        self.anio_evaluar.setRange(0, 60)
        self.anio_evaluar.setValue(10)
        btn_relleno = QPushButton(
            "Calcular lixiviados y gases (usa proyección de generación de la pestaña 1)"
        )
        btn_relleno.clicked.connect(self._calcular_relleno)
        form_relleno.addRow("Área del relleno:", self.area_relleno)
        form_relleno.addRow("Precipitación anual:", self.precipitacion)
        form_relleno.addRow("Coeficiente de infiltración:", self.coef_infiltracion)
        form_relleno.addRow("Constante k (LandGEM):", self.k_landgem)
        form_relleno.addRow("Capacidad L0 (LandGEM):", self.l0_landgem)
        form_relleno.addRow("Años de vida útil del relleno:", self.anios_vida_util)
        form_relleno.addRow("Año a evaluar (desde apertura):", self.anio_evaluar)
        form_relleno.addRow(btn_relleno)
        grupo_relleno.setLayout(form_relleno)
        layout.addWidget(grupo_relleno)

        self.resultado_relleno = QTextEdit()
        self.resultado_relleno.setReadOnly(True)
        self.resultado_relleno.setMaximumHeight(140)
        layout.addWidget(self.resultado_relleno)

    def _mostrar_factores_referencia(self):
        texto = "Factores de referencia típicos (kg CO₂eq evitado por kg reciclado):\n"
        for nombre, factor in FACTORES_EMISION_DEFAULT.items():
            texto += f"  {nombre}: {factor}\n"
        texto += "\n(Ajusta el nombre y factor arriba y presiona 'Agregar material'.)"
        self.resultado_huella.setPlainText(texto)

    def _agregar_material(self):
        if not self.mat_nombre.text().strip():
            QMessageBox.warning(self, "Falta información", "Ingresa el nombre del material.")
            return
        m = MaterialEmisionEvitada(
            self.mat_nombre.text().strip(), self.mat_kg_mes.value(), self.mat_factor.value()
        )
        self.huella.materiales.append(m)
        row = self.tabla_ambiental.rowCount()
        self.tabla_ambiental.insertRow(row)
        self.tabla_ambiental.setItem(row, 0, QTableWidgetItem("Reciclable"))
        self.tabla_ambiental.setItem(row, 1, QTableWidgetItem(m.nombre))
        self.tabla_ambiental.setItem(
            row, 2, QTableWidgetItem(f"{m.kg_mensuales_reciclados} kg/mes @ {m.factor_kg_co2_por_kg} kgCO2/kg")
        )
        self.mat_nombre.clear()

    def _usar_distancia_rutas(self):
        if not self.tab_rutas.puntos or len(self.tab_rutas.puntos) < 2:
            QMessageBox.warning(
                self, "Sin ruta calculada",
                "Ve a la pestaña 'Rutas', fija el depósito, agrega puntos y optimiza primero."
            )
            return
        try:
            resultado = optimizar_rutas(
                self.tab_rutas.puntos,
                [self.tab_rutas.cap_camion.value()] * self.tab_rutas.num_camiones.value(),
                usar_osrm=self.tab_rutas.usar_osrm.isChecked(),
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return
        self.dist_optimizada.setValue(resultado.distancia_total_flota_km)
        self.resultado_huella.setPlainText(
            f"Distancia optimizada aplicada: {resultado.distancia_total_flota_km} km/día.\n"
            f"Ingresa manualmente la distancia SIN optimizar (ej. las rutas actuales/históricas) "
            f"para comparar, y presiona 'Calcular huella de carbono'."
        )

    def _calcular_huella(self):
        self.huella.distancia_sin_optimizar_km_dia = self.dist_sin_optimizar.value()
        self.huella.distancia_optimizada_km_dia = self.dist_optimizada.value()
        self.huella.consumo_diesel_l_por_km = self.consumo_diesel.value()

        r = self.huella.resumen()
        texto = (
            f"CO₂ evitado por reciclaje: {r['co2_evitado_reciclaje_kg_mes']:.1f} kg/mes\n\n"
            f"Km ahorrados por optimización de rutas: {r['km_ahorrados_dia']:.1f} km/día\n"
            f"Diésel ahorrado: {r['diesel_ahorrado_l_mes']:.1f} L/mes\n"
            f"CO₂ evitado por rutas: {r['co2_evitado_rutas_kg_mes']:.1f} kg/mes\n\n"
            f"TOTAL CO₂ EVITADO: {r['co2_evitado_total_kg_mes']:.1f} kg/mes "
            f"({r['co2_evitado_total_ton_anio']:.2f} ton/año)\n"
        )
        self.resultado_huella.setPlainText(texto)

    def _calcular_relleno(self):
        lix = ParametrosLixiviado(
            area_relleno_m2=self.area_relleno.value(),
            precipitacion_anual_mm=self.precipitacion.value(),
            coeficiente_infiltracion_pct=self.coef_infiltracion.value(),
        )
        r_lix = lix.resumen()

        toneladas_dia = self.tab_generacion.proyecto.total_diario_toneladas()
        if toneladas_dia <= 0:
            QMessageBox.warning(
                self, "Sin generación calculada",
                "Ve a la pestaña 'Generación' y calcula el volumen proyectado primero."
            )
            return
        # Masa anual dispuesta en el relleno, asumiendo generación ~constante por año
        # (usa el promedio de la proyección multianual de la pestaña 1 para cada año)
        proyeccion = self.tab_generacion.proyecto.proyeccion_multianual(self.anios_vida_util.value())
        masas_anuales_ton = [p["toneladas_dia"] * 365 for p in proyeccion[: self.anios_vida_util.value()]]

        landgem = ParametrosLandGEM(
            k_decaimiento_anual=self.k_landgem.value(),
            l0_m3_ch4_por_mg=self.l0_landgem.value(),
        )
        anio_eval = min(self.anio_evaluar.value(), len(masas_anuales_ton) - 1) if masas_anuales_ton else 0
        q_ch4 = landgem.generacion_metano_m3_anio(masas_anuales_ton, anio_eval)
        kg_ch4 = q_ch4 * 0.68
        co2eq_ton = (kg_ch4 * 28) / 1000.0

        texto = (
            f"LIXIVIADOS (balance hídrico simplificado):\n"
            f"  Volumen anual estimado: {r_lix['volumen_lixiviado_anual_m3']:.1f} m³/año\n"
            f"  Caudal promedio: {r_lix['caudal_promedio_m3_dia']:.2f} m³/día\n\n"
            f"GASES DE RELLENO (modelo LandGEM, año {anio_eval} desde apertura):\n"
            f"  Generación de metano: {q_ch4:,.0f} m³ CH₄/año\n"
            f"  Equivalente en CO₂eq: {co2eq_ton:,.1f} ton CO₂eq/año\n\n"
            f"⚠️ Estos son valores de orden de magnitud con parámetros típicos de referencia "
            f"(EPA LandGEM). Para diseño de ingeniería o cumplimiento regulatorio, ajusta k y L0 "
            f"con un estudio de caracterización de residuos y datos climáticos del sitio específico."
        )
        self.resultado_relleno.setPlainText(texto)

    # --- Persistencia ---
    def get_state(self) -> dict:
        from dataclasses import asdict
        return {
            "materiales": [asdict(m) for m in self.huella.materiales],
            "dist_sin_optimizar": self.dist_sin_optimizar.value(),
            "dist_optimizada": self.dist_optimizada.value(),
            "consumo_diesel": self.consumo_diesel.value(),
            "area_relleno": self.area_relleno.value(),
            "precipitacion": self.precipitacion.value(),
            "coef_infiltracion": self.coef_infiltracion.value(),
            "k_landgem": self.k_landgem.value(),
            "l0_landgem": self.l0_landgem.value(),
            "anios_vida_util": self.anios_vida_util.value(),
            "anio_evaluar": self.anio_evaluar.value(),
        }

    def load_state(self, estado: dict) -> None:
        self.huella = HuellaCarbono()
        self.tabla_ambiental.setRowCount(0)
        for d in estado.get("materiales", []):
            m = MaterialEmisionEvitada(**d)
            self.huella.materiales.append(m)
            row = self.tabla_ambiental.rowCount()
            self.tabla_ambiental.insertRow(row)
            self.tabla_ambiental.setItem(row, 0, QTableWidgetItem("Reciclable"))
            self.tabla_ambiental.setItem(row, 1, QTableWidgetItem(m.nombre))
            self.tabla_ambiental.setItem(
                row, 2,
                QTableWidgetItem(f"{m.kg_mensuales_reciclados} kg/mes @ {m.factor_kg_co2_por_kg} kgCO2/kg")
            )
        self.dist_sin_optimizar.setValue(estado.get("dist_sin_optimizar", 0.0))
        self.dist_optimizada.setValue(estado.get("dist_optimizada", 0.0))
        self.consumo_diesel.setValue(estado.get("consumo_diesel", 0.35))
        self.area_relleno.setValue(estado.get("area_relleno", 50000))
        self.precipitacion.setValue(estado.get("precipitacion", 1400))
        self.coef_infiltracion.setValue(estado.get("coef_infiltracion", 20))
        self.k_landgem.setValue(estado.get("k_landgem", 0.05))
        self.l0_landgem.setValue(estado.get("l0_landgem", 100))
        self.anios_vida_util.setValue(estado.get("anios_vida_util", 15))
        self.anio_evaluar.setValue(estado.get("anio_evaluar", 10))


# ---------------------------------------------------------------------
# PESTAÑA 6: Social y Demográfico
# ---------------------------------------------------------------------
class TabSocial(QWidget):
    def __init__(self, tab_generacion: TabGeneracion):
        super().__init__()
        self.tab_generacion = tab_generacion
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)

        panel_izq = QVBoxLayout()

        info = QLabel(
            "Este mapa usa las coordenadas (lat/lon) ingresadas opcionalmente\n"
            "al agregar cada zona en la pestaña '1. Generación de Residuos'.\n"
            "Zonas sin coordenadas (0,0) no aparecen en el mapa."
        )
        panel_izq.addWidget(info)

        btn_generacion = QPushButton("Generar mapa de calor: Generación de residuos")
        btn_generacion.clicked.connect(lambda: self._generar_mapa("generacion"))
        panel_izq.addWidget(btn_generacion)

        btn_deficit = QPushButton("Generar mapa de calor: Déficit de reciclaje (zonas residenciales)")
        btn_deficit.clicked.connect(lambda: self._generar_mapa("deficit"))
        panel_izq.addWidget(btn_deficit)

        self.tabla_ranking = QTableWidget(0, 3)
        self.tabla_ranking.setHorizontalHeaderLabels(["Zona", "Tipo", "Valor"])
        self.tabla_ranking.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        panel_izq.addWidget(QLabel("Ranking (top 10):"))
        panel_izq.addWidget(self.tabla_ranking)

        panel_izq_widget = QWidget()
        panel_izq_widget.setLayout(panel_izq)

        self.mapa_view = QWebEngineView()
        self._render_mapa_vacio()

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(panel_izq_widget)
        splitter.addWidget(self.mapa_view)
        splitter.setSizes([420, 700])
        layout.addWidget(splitter)

    def _render_mapa_vacio(self):
        m = folium.Map(location=[18.4655, -69.8977], zoom_start=11)
        self._mostrar_mapa(m)

    def _mostrar_mapa(self, mapa: folium.Map):
        import os, tempfile
        tmp_path = os.path.join(tempfile.gettempdir(), "mapa_calor_social.html")
        mapa.save(tmp_path)
        self.mapa_view.load(f"file://{tmp_path}")

    def _generar_mapa(self, tipo: str):
        zonas = self.tab_generacion.proyecto.zonas_georreferenciadas()
        if not zonas:
            QMessageBox.warning(
                self, "Sin coordenadas",
                "Ninguna zona tiene coordenadas asignadas. Ve a la pestaña 'Generación', "
                "y al agregar cada zona, ingresa su latitud y longitud."
            )
            return

        if tipo == "generacion":
            puntos = puntos_calor_generacion(zonas)
            ranking = ranking_zonas_por_generacion(zonas)
            columna_valor = lambda z: f"{z['generacion_kg_dia']:.1f} kg/día"
            titulo_capa = "Generación de residuos"
        else:
            puntos = puntos_calor_deficit_reciclaje(zonas)
            ranking = ranking_zonas_por_deficit_reciclaje(zonas)
            columna_valor = lambda z: (
                f"{z['generacion_kg_dia'] * (1 - z['tasa_reciclaje_pct']/100):.1f} kg/día sin reciclar"
            )
            titulo_capa = "Déficit de reciclaje"
            if not puntos:
                QMessageBox.information(
                    self, "Sin datos de reciclaje",
                    "Ninguna zona residencial tiene una tasa de reciclaje asignada (>0%). "
                    "Ve a la pestaña 'Generación' y complétala al agregar zonas residenciales."
                )
                return

        centro_lat = sum(p[0] for p in puntos) / len(puntos)
        centro_lon = sum(p[1] for p in puntos) / len(puntos)
        m = folium.Map(location=[centro_lat, centro_lon], zoom_start=12)
        HeatMap(puntos, radius=35, blur=25).add_to(m)
        for z in zonas:
            folium.CircleMarker(
                [z["lat"], z["lon"]], radius=4, color="black", fill=True,
                popup=f"{z['nombre']} ({z['tipo']}) — {z['generacion_kg_dia']:.1f} kg/día",
            ).add_to(m)
        self._mostrar_mapa(m)

        self.tabla_ranking.setRowCount(0)
        for z in ranking:
            row = self.tabla_ranking.rowCount()
            self.tabla_ranking.insertRow(row)
            self.tabla_ranking.setItem(row, 0, QTableWidgetItem(z["nombre"]))
            self.tabla_ranking.setItem(row, 1, QTableWidgetItem(z["tipo"]))
            self.tabla_ranking.setItem(row, 2, QTableWidgetItem(columna_valor(z)))

    # Esta pestaña no tiene estado propio que guardar: todos sus datos
    # (coordenadas, tasas de reciclaje) viven en la pestaña de Generación.


# ---------------------------------------------------------------------
# VENTANA PRINCIPAL
# ---------------------------------------------------------------------
class VentanaPrincipal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Viabilidad de Gestión de Residuos — MVP")
        self.resize(1450, 900)

        self.tab_generacion = TabGeneracion()
        self.tab_capacidad = TabCapacidad(self.tab_generacion)
        self.tab_rutas = TabRutas()
        self.tab_financiero = TabFinanciero(self.tab_generacion)
        self.tab_ambiental = TabAmbiental(self.tab_generacion, self.tab_rutas)
        self.tab_social = TabSocial(self.tab_generacion)

        tabs = QTabWidget()
        tabs.addTab(self.tab_generacion, "1. Generación de Residuos")
        tabs.addTab(self.tab_capacidad, "2. Capacidad de Infraestructura")
        tabs.addTab(self.tab_rutas, "3. Optimización de Rutas")
        tabs.addTab(self.tab_financiero, "4. Económico y Financiero")
        tabs.addTab(self.tab_ambiental, "5. Ambiental")
        tabs.addTab(self.tab_social, "6. Social y Demográfico")

        self.setCentralWidget(tabs)
        self._build_menu()
        self._ruta_actual = None

    def _build_menu(self):
        menu_archivo = self.menuBar().addMenu("&Archivo")
        accion_guardar = menu_archivo.addAction("Guardar proyecto...")
        accion_guardar.triggered.connect(self._guardar_proyecto)
        accion_abrir = menu_archivo.addAction("Abrir proyecto...")
        accion_abrir.triggered.connect(self._abrir_proyecto)

    def _guardar_proyecto(self):
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Guardar proyecto", "proyecto_residuos.json", "Proyecto JSON (*.json)"
        )
        if not ruta:
            return
        estado = {
            "generacion": self.tab_generacion.get_state(),
            "capacidad": self.tab_capacidad.get_state(),
            "rutas": self.tab_rutas.get_state(),
            "financiero": self.tab_financiero.get_state(),
            "ambiental": self.tab_ambiental.get_state(),
        }
        try:
            guardar_proyecto(ruta, estado)
            QMessageBox.information(self, "Guardado", f"Proyecto guardado en:\n{ruta}")
        except Exception as e:
            QMessageBox.critical(self, "Error al guardar", str(e))

    def _abrir_proyecto(self):
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Abrir proyecto", "", "Proyecto JSON (*.json)"
        )
        if not ruta:
            return
        try:
            estado = cargar_proyecto(ruta)
            self.tab_generacion.load_state(estado.get("generacion", {}))
            self.tab_capacidad.load_state(estado.get("capacidad", {}))
            self.tab_rutas.load_state(estado.get("rutas", {}))
            self.tab_financiero.load_state(estado.get("financiero", {}))
            self.tab_ambiental.load_state(estado.get("ambiental", {}))
            QMessageBox.information(self, "Proyecto cargado", f"Proyecto cargado desde:\n{ruta}")
        except Exception as e:
            QMessageBox.critical(self, "Error al abrir", str(e))


def main():
    app = QApplication(sys.argv)
    ventana = VentanaPrincipal()
    ventana.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
