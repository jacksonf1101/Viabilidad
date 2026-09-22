; ==========================================================
; Instalador de "Viabilidad de Gestion de Residuos"
; Compilar con Inno Setup (https://jrsoftware.org/isinfo.php):
;   1. Primero corre build_windows.bat (genera dist\ViabilidadResiduos\)
;   2. Abre este archivo con Inno Setup Compiler y presiona "Compile"
;      (o desde consola: ISCC.exe installer.iss)
;   3. El instalador queda en: installer_output\ViabilidadResiduos_Setup.exe
; ==========================================================

#define MyAppName "Viabilidad de Gestion de Residuos"
#define MyAppVersion "1.0"
#define MyAppPublisher "Jackson - Automatizacion de Residuos"
#define MyAppExeName "ViabilidadResiduos.exe"

[Setup]
AppId={{B8F1D3A2-4C5E-4A9B-9F1C-1234567890AB}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=ViabilidadResiduos_Setup
Compression=lzma2
SolidCompression=yes
SetupIconFile=icon.ico
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el Escritorio"; GroupDescription: "Accesos directos:"; Flags: unchecked

[Files]
Source: "dist\ViabilidadResiduos\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Ejecutar {#MyAppName}"; Flags: nowait postinstall skipifsilent
