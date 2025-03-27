@echo off
rem Script para iniciar el bot de WhatsApp con ngrok en Windows

echo 🚀 Iniciando bot de WhatsApp...

rem Verificar que Python está instalado
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: Python no está instalado o no está en el PATH
    exit /b 1
)

rem Verificar que ngrok está instalado
where ngrok >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: ngrok no está instalado o no está en el PATH
    echo Descárgalo desde https://ngrok.com/download
    exit /b 1
)

rem Crear directorios necesarios
if not exist data mkdir data
if not exist logs mkdir logs

rem Cargar variables de entorno del archivo .env
if exist .env (
    for /f "tokens=*" %%a in (.env) do (
        set "%%a"
    )
) else (
    echo Archivo .env no encontrado, usando valores por defecto
)

rem Asignar valores por defecto si no están definidos
if not defined FLASK_PORT set FLASK_PORT=8000
if not defined NGROK_PORT set NGROK_PORT=8000
if not defined NGROK_REGION set NGROK_REGION=us

echo 🔌 Puerto Flask: %FLASK_PORT%
echo 🌐 Configuración ngrok: Puerto %NGROK_PORT%, Región %NGROK_REGION%

rem Iniciar la aplicación Flask en una nueva ventana
echo 📱 Iniciando servidor Flask...
start "Flask Server" cmd /c "python run.py"

rem Dar tiempo para que Flask inicie
timeout /t 3 >nul

rem Iniciar ngrok en una nueva ventana
echo 🔗 Iniciando ngrok...
if not defined NGROK_DOMAIN (
    rem Usar un túnel temporal
    start "Ngrok Tunnel" cmd /c "ngrok http --region=%NGROK_REGION% %NGROK_PORT%"
) else (
    rem Usar dominio estático configurado
    start "Ngrok Tunnel" cmd /c "ngrok http --region=%NGROK_REGION% --domain=%NGROK_DOMAIN% %NGROK_PORT%"
)

echo.
echo ✅ Sistema iniciado correctamente
echo 📝 URL de webhook: https://TU-DOMINIO-NGROK/webhook
echo ⚠️ Recuerda configurar esta URL en el panel de desarrollador de Meta
echo.
echo 👉 Cierra las ventanas de comandos para detener el sistema
echo.

pause