@echo off
setlocal enabledelayedexpansion

echo ======================================================================
echo  COMPILADOR OTIMIZADO ALTUS PC OPTIMIZER
echo ======================================================================1
echo.

cd /d "%~dp0"

echo [1/3] Limpando pastas temporarias de compilacao e encerrando instancias ativas...
taskkill /f /im ALTUS-PC-OPTIMIZER.exe >nul 2>&1
timeout /t 1 /nobreak >nul
if exist "build" rmdir /s /q "build"
if exist "dist\ALTUS-PC-OPTIMIZER.exe" del /f /q "dist\ALTUS-PC-OPTIMIZER.exe"

echo.
echo [2/3] Compilando executavel unico ultra-otimizado com PyInstaller...
python -m PyInstaller ^
    --noconfirm ^
    --onefile ^
    --windowed ^
    --name "ALTUS-PC-OPTIMIZER" ^
    --icon "src/resources/icons/app.ico" ^
    --add-data "src/resources;src/resources" ^
    --hidden-import "PySide6.QtCore" ^
    --hidden-import "PySide6.QtGui" ^
    --hidden-import "PySide6.QtWidgets" ^
    --hidden-import "psutil" ^
    --hidden-import "platformdirs" ^
    --exclude-module "numpy" ^
    --exclude-module "scipy" ^
    --exclude-module "matplotlib" ^
    --exclude-module "pandas" ^
    --exclude-module "cv2" ^
    --exclude-module "torch" ^
    --exclude-module "PySide6.QtWebEngineCore" ^
    --exclude-module "PySide6.QtWebEngineWidgets" ^
    --exclude-module "PySide6.QtWebEngineQuick" ^
    --exclude-module "PySide6.QtPdf" ^
    --exclude-module "PySide6.QtPdfWidgets" ^
    --exclude-module "PySide6.QtQuick" ^
    --exclude-module "PySide6.QtQml" ^
    --exclude-module "PySide6.QtNetworkAuth" ^
    --exclude-module "PySide6.QtSql" ^
    --exclude-module "PySide6.QtTest" ^
    --exclude-module "PySide6.Qt3DCore" ^
    --exclude-module "PySide6.QtSensors" ^
    --exclude-module "PySide6.QtPositioning" ^
    --exclude-module "PySide6.QtBluetooth" ^
    --exclude-module "PySide6.QtNfc" ^
    --exclude-module "PySide6.QtSerialPort" ^
    --exclude-module "PySide6.QtMultimedia" ^
    --exclude-module "PySide6.QtMultimediaWidgets" ^
    --clean ^
    main.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERRO] Falha na compilacao com o PyInstaller.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [3/3] Validando executavel gerado...
if exist "dist\ALTUS-PC-OPTIMIZER.exe" (
    echo.
    echo ======================================================================
    echo  SUCESSO: ALTUS-PC-OPTIMIZER.exe gerado com sucesso!
    echo  Localizacao: %~dp0dist\ALTUS-PC-OPTIMIZER.exe
    echo ======================================================================
) else (
    echo [ERRO] Executavel dist\ALTUS-PC-OPTIMIZER.exe nao foi encontrado.
    pause
    exit /b 1
)

echo Concluido!
