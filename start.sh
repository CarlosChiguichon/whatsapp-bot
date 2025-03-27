#!/bin/bash
# Script para iniciar el bot de WhatsApp con ngrok

# Cargar variables de entorno
source .env 2>/dev/null || echo "Archivo .env no encontrado, usando valores por defecto"

# Asignar valores por defecto si no están definidos
FLASK_PORT=${FLASK_PORT:-8000}
NGROK_PORT=${NGROK_PORT:-8000}
NGROK_REGION=${NGROK_REGION:-us}
NGROK_DOMAIN=${NGROK_DOMAIN:-""}

# Verificar que ngrok esté instalado
if ! command -v ngrok &> /dev/null; then
    echo "Error: ngrok no está instalado. Por favor, instálalo desde https://ngrok.com/download"
    exit 1
fi

# Crear directorios necesarios
mkdir -p data logs

# Mostrar información de inicio
echo "🚀 Iniciando bot de WhatsApp..."
echo "🔌 Puerto Flask: $FLASK_PORT"
echo "🌐 Configuración ngrok: Puerto $NGROK_PORT, Región $NGROK_REGION"

# Iniciar la aplicación Flask en segundo plano
echo "📱 Iniciando servidor Flask..."
python run.py &
FLASK_PID=$!

# Dar tiempo para que Flask inicie
sleep 2

# Iniciar ngrok
echo "🔗 Iniciando ngrok..."
if [ -z "$NGROK_DOMAIN" ]; then
    # Usar un túnel temporal
    ngrok http --region=$NGROK_REGION $NGROK_PORT &
else
    # Usar dominio estático configurado
    ngrok http --region=$NGROK_REGION --domain=$NGROK_DOMAIN $NGROK_PORT &
fi
NGROK_PID=$!

# Mensaje informativo
echo ""
echo "✅ Sistema iniciado correctamente"
echo "📝 URL de webhook: https://TU-DOMINIO-NGROK/webhook"
echo "⚠️ Recuerda configurar esta URL en el panel de desarrollador de Meta"
echo ""
echo "👉 Presiona Ctrl+C para detener el sistema"

# Función para manejar la terminación
function cleanup {
    echo ""
    echo "🛑 Deteniendo servicios..."
    kill $FLASK_PID 2>/dev/null
    kill $NGROK_PID 2>/dev/null
    echo "👋 ¡Hasta pronto!"
    exit 0
}

# Capturar señal de terminación
trap cleanup SIGINT SIGTERM

# Mantener el script en ejecución
wait