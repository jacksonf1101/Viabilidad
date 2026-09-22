@echo off
REM ==========================================================
REM  Compilar Viabilidad de Gestion de Residuos como .exe
REM  Ejecutar este script en una PC Windows con Python instalado
REM ==========================================================

echo.
echo [1/4] Creando entorno virtual...
python -m venv venv
call venv\Scripts\activate.bat

echo.
echo [2/4] Instalando dependencias...
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

echo.
echo [3/4] Compilando .exe (esto puede tardar varios minutos)...
pyinstaller --noconfirm --windowed --onedir ^
    --name "ViabilidadResiduos" ^
    --icon=icon.ico ^
    --collect-all PySide6 ^
    --collect-all ortools ^
    --collect-all folium ^
    main.py

echo.
echo [4/4] Listo. El ejecutable esta en: dist\ViabilidadResiduos\ViabilidadResiduos.exe
echo.
echo Para crear un INSTALADOR (Setup.exe con icono, accesos directos y
echo desinstalador), instala Inno Setup (https://jrsoftware.org/isinfo.php)
echo y luego abre installer.iss con el, o ejecuta:
echo    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
echo.
pause
