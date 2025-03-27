"""
Punto de entrada principal para la aplicación Flask del bot de WhatsApp.
"""
import logging
from app import create_app

# Crear la aplicación Flask
app = create_app()

if __name__ == "__main__":
    logging.info("Iniciando servidor Flask...")
    app.run(host="0.0.0.0", port=8000)