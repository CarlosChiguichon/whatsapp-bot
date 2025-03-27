"""
Configuración centralizada de la aplicación.
"""
import os
import sys
import logging
from dotenv import load_dotenv

def load_config(app):
    """
    Carga la configuración desde variables de entorno con validación.
    
    Args:
        app (Flask): Instancia de la aplicación Flask
    """
    # Cargar variables de entorno desde .env
    load_dotenv()
    
    # Variables requeridas para el funcionamiento de la aplicación
    required_vars = [
        "ACCESS_TOKEN",
        "APP_ID",
        "APP_SECRET",
        "PHONE_NUMBER_ID",
        "VERSION",
        "VERIFY_TOKEN"
    ]
    
    # Verificar variables requeridas
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logging.error(f"Faltan variables de entorno requeridas: {', '.join(missing_vars)}")
        sys.exit(1)
    
    # Cargar variables en la configuración de Flask
    app.config["ACCESS_TOKEN"] = os.getenv("ACCESS_TOKEN")
    app.config["APP_ID"] = os.getenv("APP_ID")
    app.config["APP_SECRET"] = os.getenv("APP_SECRET")
    app.config["PHONE_NUMBER_ID"] = os.getenv("PHONE_NUMBER_ID")
    app.config["VERSION"] = os.getenv("VERSION")
    app.config["VERIFY_TOKEN"] = os.getenv("VERIFY_TOKEN")
    
    # Variables opcionales con valores por defecto
    app.config["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")
    app.config["OPENAI_ASSISTANT_ID"] = os.getenv("OPENAI_ASSISTANT_ID", "")
    app.config["ODOO_WEBHOOK_URL_TICKETS"] = os.getenv("ODOO_WEBHOOK_URL_TICKETS", "")
    
    # Configuración del nivel de log basado en entorno
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    configure_logging(log_level)
    
    # Modo de depuración
    app.debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    
    logging.info("Configuración cargada correctamente")

def configure_logging(log_level):
    """
    Configura el sistema de logging.
    
    Args:
        log_level (str): Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Convertir el nivel de string a constante de logging
    numeric_level = getattr(logging, log_level, logging.INFO)
    
    # Configuración básica de logging
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("app.log")
        ]
    )
    
    # Silenciar logs excesivamente detallados de bibliotecas
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    
    logging.info(f"Logging configurado en nivel: {log_level}")