from flask import Flask
import logging
from app.config import load_config
from app.integrations.whatsapp import init_whatsapp_config
from app.core.queue_manager import QueueManager, RateLimiter
from app.core.circuit_breaker import CircuitBreaker
from app.core.knowledge_base import ProductKnowledgeBase
from app.core.metrics import register_metrics

def create_app():
    """Crea y configura la aplicación Flask con todas las mejoras."""
    app = Flask(__name__)
    
    # Cargar configuraciones
    load_config(app)
    
    # Inicializar componentes principales
    init_components(app)
    
    # Registrar blueprints
    register_blueprints(app)
    
    # Registrar métricas
    register_metrics(app)
    
    logging.info("Aplicación Flask inicializada correctamente")
    return app

def init_components(app):
    """Inicializa todos los componentes del sistema."""
    # Sistema de colas con Redis
    redis_url = app.config.get("REDIS_URL", "redis://localhost:6379")
    app.queue_manager = QueueManager(redis_url)
    app.rate_limiter = RateLimiter(app.queue_manager.redis_client)
    
    # Registrar procesadores de colas
    from app.workers import process_whatsapp_message, process_odoo_webhook
    app.queue_manager.register_processor("whatsapp_incoming", process_whatsapp_message)
    app.queue_manager.register_processor("odoo_webhooks", process_odoo_webhook)
    
    # Iniciar workers
    app.queue_manager.start_workers(["whatsapp_incoming", "odoo_webhooks"])
    
    # Circuit breakers para servicios externos
    app.circuit_breakers = {
        'odoo_tickets': CircuitBreaker("odoo_tickets", failure_threshold=3),
        'odoo_leads': CircuitBreaker("odoo_leads", failure_threshold=3),
        'openai': CircuitBreaker("openai", failure_threshold=5)
    }
    
    # Base de conocimientos
    app.knowledge_base = ProductKnowledgeBase()
    init_knowledge_base(app)
    
    # Configuración de WhatsApp
    init_whatsapp_config(app)
    
def init_knowledge_base(app):
    """Inicializa la base de conocimientos con productos."""
    import os
    kb_path = "data/product_index.pkl"
    
    if os.path.exists(kb_path):
        app.knowledge_base.load(kb_path)
    else:
        from app.data.products_loader import load_product_catalog
        documents = load_product_catalog()
        app.knowledge_base.build_index(documents)
        app.knowledge_base.save(kb_path)

def register_blueprints(app):
    """Registra todos los blueprints de la aplicación."""
    from app.views.webhook import webhook_bp
    from app.views.health import health_bp
    from app.views.dashboard import dashboard_bp
    
    app.register_blueprint(webhook_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(dashboard_bp)
    logging.info("Blueprints registrados")