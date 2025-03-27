"""
Inicialización de la aplicación Flask usando el patrón Factory.
"""
from flask import Flask
import logging

from app.config import load_config
from app.integrations.whatsapp import init_whatsapp_config

def create_app():
    """
    Crea y configura la aplicación Flask.
    
    Returns:
        Flask: Instancia configurada de la aplicación Flask
    """
    app = Flask(__name__)
    
    # Cargar configuraciones y configurar logging
    load_config(app)
    
    # Inicializar configuración de WhatsApp para hilos en segundo plano
    init_whatsapp_config(app)
    
    # Registrar blueprints
    register_blueprints(app)
    
    logging.info("Aplicación Flask inicializada correctamente")
    return app

def register_blueprints(app):
    """
    Registra todos los blueprints de la aplicación.
    
    Args:
        app (Flask): Instancia de la aplicación Flask
    """
    from app.views.webhook import webhook_bp
    from app.views.health import health_bp
    
    app.register_blueprint(webhook_bp)
    app.register_blueprint(health_bp)
    logging.info("Blueprints registrados")