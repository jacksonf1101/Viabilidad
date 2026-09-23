# Software de Viabilidad de Gestión de Residuos — MVP

Aplicación de escritorio (Python + PySide6) que cubre los módulos
**Técnico/Logístico** y **Económico/Financiero** del sistema de
viabilidad de manejo de residuos:

1. **Generación de residuos** — estima toneladas/día por zona
   residencial, comercial e industrial, con proyección a 5 años.
2. **Capacidad de infraestructura** — compara el volumen proyectado
   contra la capacidad real de la flota de camiones y de la(s)
   planta(s) de transferencia, con alertas automáticas (OK / ALERTA /
   CRÍTICO) y sugerencia de camiones adicionales.
3. **Optimización de rutas** — calcula las rutas de recolección más
   eficientes con restricción de capacidad por camión (algoritmo
   CVRP vía Google OR-Tools). El mapa resultante (Leaflet/OpenStreetMap)
   se abre automáticamente en tu navegador predeterminado.
4. **Económico y Financiero** — costo por tonelada, ingresos por
   venta de reciclables y biogás, simulación de tarifa de aseo
   (equilibrio y con margen), balance mensual y retorno de inversión
   (ROI) en años.
5. **Ambiental** — CO₂ evitado por reciclaje y por optimización de
   rutas; lixiviados (balance hídrico simplificado) y gases de
   relleno sanitario (modelo LandGEM de la EPA).
6. **Social y Demográfico** — mapas de calor (abiertos en tu navegador)
   que muestran qué zonas generan más residuos o tienen menor tasa de
   reciclaje, con ranking para priorizar campañas educativas.

Los seis módulos están **conectados entre sí**: la generación de
residuos (pestaña 1) alimenta a capacidad, finanzas, ambiental y
social; la optimización de rutas (pestaña 3) alimenta directamente
el cálculo de CO₂ evitado (pestaña 5).

Además, el menú **Archivo → Guardar/Abrir proyecto** permite guardar
todo el estado de las 4 pestañas en un archivo `.json` y continuar
el trabajo después, sin perder los datos ingresados.

---

## Instalación

Requiere **Python 3.10 o superior**.

```bash
cd waste_viability_mvp
python -m venv venv
source venv/bin/activate      # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Ejecución

```bash
python main.py
```

Se abrirá la ventana principal con seis pestañas (Generación,
Capacidad, Rutas, Económico y Financiero, Ambiental, Social y
Demográfico).

### Guardar y continuar un proyecto
Usa **Archivo → Guardar proyecto...** para exportar todo lo
ingresado (zonas, flota, plantas, puntos de ruta, costos, tarifas)
a un archivo `.json`. Con **Archivo → Abrir proyecto...** lo vuelves
a cargar exactamente como lo dejaste, en cualquier momento.

---

## Notas técnicas

### Módulo de generación
Los factores por defecto (0.9 kg/hab/día residencial, 15 kg/local/día
comercial, 2.5 kg/empleado/día industrial) son editables en la
interfaz — ajústalos con datos reales de estudios de caracterización
si los tienes, o dejo los valores de referencia para RD si no.

### Módulo de capacidad
- "Utilización" = volumen proyectado ÷ capacidad disponible.
- < 80% = OK, 80–100% = ALERTA, > 100% = CRÍTICO.
- El campo "disponibilidad" del camión representa el % de la flota
  que está operativa (no en mantenimiento).

### Módulo de rutas (VRP)
- Usa **Google OR-Tools** (algoritmo CVRP — Capacitated Vehicle
  Routing Problem) para asignar puntos de recolección a camiones
  respetando su capacidad, minimizando la distancia total.
- Si hay conexión a internet, obtiene distancias **reales por calle**
  vía OSRM (Open Source Routing Machine, servidor público de
  demostración). Si no hay conexión, usa distancia en línea recta
  con un factor de corrección de 1.3x (aproximación razonable para
  trazado urbano).
- **Importante:** el servidor público de OSRM (`router.project-osrm.org`)
  es gratuito pero de uso limitado y sin garantía de disponibilidad.
  Para uso productivo/comercial se recomienda migrar a:
  - Un servidor OSRM propio (self-hosted, gratis, requiere servidor), o
  - Google Maps Distance Matrix API / Mapbox (de pago, más robusto y
    con tráfico en tiempo real).
- El "tráfico" actual se aproxima con una velocidad promedio fija
  (25 km/h). Para tráfico en tiempo real se necesita una API paga
  (Google, TomTom, HERE) — lo dejo como siguiente iteración.

### Sobre los mapas (rutas y calor)
Los mapas **se abren en tu navegador predeterminado** (Chrome, Edge,
Firefox...) en vez de mostrarse dentro de la ventana del programa. Esta
decisión fue deliberada: la alternativa (un mapa embebido con
QtWebEngine/Chromium) depende de la aceleración por GPU de cada PC, y en
varias máquinas con drivers de video limitados el mapa cargaba pero
quedaba en blanco, sin ningún error visible. Abrirlo en el navegador del
sistema es 100% confiable porque usa el motor de renderizado que ya
funciona en esa PC — y de paso, el `.exe` queda más liviano y rápido de
instalar al no tener que empaquetar un Chromium completo.

Cada vez que optimizas rutas o generas un mapa de calor, se abre una
pestaña nueva del navegador automáticamente. El botón "Volver a abrir
el último mapa" (en cada pestaña) permite reabrirlo sin tener que
recalcular, por si cerraste la pestaña del navegador sin querer.

---

## Notas del módulo económico/financiero

- **Costo por tonelada** = costos operativos totales ÷ toneladas/mes
  (usa el volumen calculado en la pestaña 1).
- **Ingresos por reciclables**: defines qué % del total de residuos
  es cada material recuperable (plástico, cartón, vidrio, metal...) y
  su precio de venta por kg; el software calcula el ingreso mensual.
- **Tarifa de equilibrio**: botón que calcula automáticamente cuánto
  debe pagar cada usuario al mes para que el sistema cubra sus costos
  exactamente (balance = 0), sin necesidad de calcularlo a mano. Puedes
  luego subir esa tarifa manualmente para generar margen de utilidad.
- **ROI**: toma el balance mensual actual (con la tarifa que hayas
  fijado) y lo proyecta contra la inversión inicial. Si el balance no
  es positivo, el software te avisa que la inversión no se recupera
  con esos parámetros en vez de mostrar un número engañoso.

## Notas del módulo ambiental

- **CO₂ evitado por reciclaje**: se define cada material reciclado
  (kg/mes) y su factor de emisión evitada (kg CO₂eq/kg) — el botón
  "Usar factores de referencia típicos" muestra valores de orden
  de magnitud (similares a EPA WARM) que puedes copiar y ajustar.
- **CO₂ evitado por rutas**: compara la distancia recorrida ANTES
  (la ingresas manualmente, ej. de tus rutas actuales) contra la
  distancia DESPUÉS de optimizar — el botón "Usar distancia
  optimizada calculada en pestaña 'Rutas'" trae automáticamente el
  resultado de la pestaña 3.
- **Lixiviados**: balance hídrico simplificado (precipitación ×
  área del relleno × % de infiltración). Es una estimación de
  orden de magnitud, no un diseño de sistema de manejo de lixiviados.
- **Gases de relleno (LandGEM)**: implementa el modelo de primer
  orden de la EPA (`Q_CH4 = Σ k·L0·M_i·exp(-k·(t-t_i))`), usando la
  proyección multianual de generación de la pestaña 1 como masa
  anual dispuesta. Los valores por defecto de k y L0 son típicos de
  referencia — **ajústalos con datos reales para cualquier uso
  regulatorio o de diseño**.

## Notas del módulo social/demográfico

- Los mapas de calor usan las coordenadas (lat/lon) que ingreses
  **opcionalmente** al agregar cada zona en la pestaña 1. Una zona
  sin coordenadas (0,0) simplemente no aparece en el mapa — puedes
  seguir usando el resto del software sin llenarlas.
- **Mapa de generación**: intensidad = kg/día generados por zona.
- **Mapa de déficit de reciclaje**: intensidad = kg/día que NO se
  reciclan, calculado con la "tasa de reciclaje actual" que
  ingreses (opcional) en cada zona residencial. Útil para priorizar
  dónde enfocar campañas educativas.
- El ranking (tabla) te da el top 10 de zonas por generación o por
  déficit de reciclaje, sin necesidad de interpretar el mapa a ojo.

## Próximos pasos sugeridos (fuera de este MVP)

- Exportar resultados (de cualquier pestaña) a PDF/Excel para informes.
- Integrar tráfico en tiempo real (API de pago) si el negocio lo
  justifica.
- Gráficas de la proyección multianual de generación, LandGEM y del
  flujo de caja (actualmente se muestran como texto/tabla).
- Capas adicionales en el mapa social (densidad poblacional, límites
  municipales/barriales reales vía shapefile).

---

## Generar el instalador .exe para Windows

Este software se desarrolló en este entorno Linux, así que el `.exe` no
puede compilarse aquí (PyInstaller no compila de forma cruzada hacia
Windows). Tienes dos rutas para obtenerlo — elige la que te sea más
cómoda:

### Opción A — Automático, sin usar Windows (recomendado)

1. Sube esta carpeta a un repositorio de GitHub (puede ser privado).
2. GitHub compilará el `.exe` automáticamente en un servidor Windows
   real usando el workflow incluido en
   `.github/workflows/build-windows.yml` (se activa solo al subir
   cambios, o manualmente desde la pestaña "Actions" → "Run workflow").
3. Cuando termine (~5-10 min), entra a la pestaña **Actions** del
   repositorio, abre la ejecución más reciente y descarga:
   - **ViabilidadResiduos-Instalador** → el `Setup.exe` listo para
     instalar (con asistente, accesos directos y desinstalador).
   - **ViabilidadResiduos-Windows** → la versión portátil (carpeta
     con el `.exe` suelto, sin instalador).

### Opción B — Compilarlo tú en una PC con Windows

1. Instala [Python 3.12](https://www.python.org/downloads/) en esa PC
   (marca "Add Python to PATH" durante la instalación).
2. Copia esta carpeta completa a la PC Windows.
3. Haz doble clic en **`build_windows.bat`** — instala todo lo
   necesario y compila el `.exe` automáticamente. Al terminar, queda
   en `dist\ViabilidadResiduos\ViabilidadResiduos.exe`.
4. (Opcional, para tener un instalador con asistente en vez del `.exe`
   suelto) Instala [Inno Setup](https://jrsoftware.org/isinfo.php),
   abre `installer.iss` con él y presiona **Compile**. El instalador
   queda en `installer_output\ViabilidadResiduos_Setup.exe`.

### Notas

- El `.exe` resultante es **portátil dentro de su carpeta**: PyInstaller
  empaqueta Python y todas las dependencias (PySide6, OR-Tools, etc.),
  así que la PC destino NO necesita tener Python instalado. Solo
  necesita conservar todos los archivos de la carpeta `ViabilidadResiduos`
  juntos (o usar el instalador, que ya se encarga de eso).
- Incluí un ícono genérico (`icon.ico`) — reemplázalo por el tuyo si
  quieres un logo propio (mismo nombre de archivo, formato `.ico`).
- El tamaño del `.exe` compilado será de aproximadamente 250-350 MB,
  porque incluye el motor de mapas (QtWebEngine, basado en Chromium).

---

## Estructura del proyecto

```
waste_viability_mvp/
├── main.py                 # Interfaz gráfica (PySide6), 6 pestañas + menú Archivo
├── modules/
│   ├── generation.py        # Cálculo de generación de residuos (+ coordenadas)
│   ├── capacity.py           # Evaluación de capacidad de infraestructura
│   ├── routing.py            # Optimización de rutas (OR-Tools + OSRM)
│   ├── financial.py          # Costo-beneficio, tarifas y ROI
│   ├── environmental.py      # Huella de carbono, lixiviados y LandGEM
│   ├── social.py              # Mapas de calor y rankings por zona
│   └── persistence.py        # Guardar/abrir proyectos en JSON
├── build_windows.bat        # Compila el .exe (correr en Windows)
├── installer.iss            # Script de Inno Setup para el instalador
├── icon.ico                  # Ícono de la aplicación
├── .github/workflows/
│   └── build-windows.yml     # Compila el .exe automáticamente en GitHub
├── requirements.txt
└── README.md
```
