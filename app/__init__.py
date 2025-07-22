from flask import Flask
import logging
from app.config import load_config
from app.integrations.whatsapp import init_whatsapp_config
from app.core.metrics import register_metrics

# Importaciones con fallbacks
try:
    from app.core.queue_manager import QueueManager, RateLimiter
except ImportError:
    # Fallback si no existe
    logging.warning("Queue manager no disponible, usando fallback")
    class QueueManager:
        def __init__(self, *args): 
            self.redis_client = None
        def register_processor(self, *args): pass
        def start_workers(self, *args): pass
    
    class RateLimiter:
        def __init__(self, *args): pass

try:
    from app.core.circuit_breaker import CircuitBreaker
except ImportError:
    logging.warning("Circuit breaker no disponible, usando fallback")
    class CircuitBreaker:
        def __init__(self, *args, **kwargs): 
            self.state = type('State', (), {'value': 'closed'})()
        def get_status(self): 
            return {'name': 'fallback', 'state': 'closed'}

try:
    from app.core.knowledge_base import ProductKnowledgeBase
except ImportError:
    logging.warning("Knowledge base no disponible, usando fallback")
    class ProductKnowledgeBase:
        def __init__(self): pass
        def build_index(self, *args): pass
        def save(self, *args): pass
        def load(self, *args): pass

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
        'openai': CircuitBreaker("openai", failure_threshold=5)
    }
    
    # Base de conocimientos
    app.knowledge_base = ProductKnowledgeBase()
    init_knowledge_base(app)
    
    # Configuración de WhatsApp
    init_whatsapp_config(app)
    
def init_knowledge_base(app):
    """Inicializa la base de conocimientos con productos."""
    try:
        import os
        kb_path = "data/product_index.pkl"
        
        if os.path.exists(kb_path):
            app.knowledge_base.load(kb_path)
        else:
            try:
                from app.data.products_loader import load_product_catalog
                documents = load_product_catalog()
                app.knowledge_base.build_index(documents)
                app.knowledge_base.save(kb_path)
            except ImportError:
                logging.warning("Products loader no disponible, usando datos por defecto")
                # Usar algunos productos por defecto
                default_docs = [
                    {"content": "Paneles solares monocristalinos alta eficiencia"},
                    {"content": "Inversores string para instalaciones residenciales"},
                    {"content": "Baterías de litio para almacenamiento de energía"}
                ]
                app.knowledge_base.build_index(default_docs)
    except Exception as e:
        logging.error(f"Error inicializando base de conocimientos: {str(e)}")

def register_blueprints(app):
    """Registra todos los blueprints de la aplicación."""
    try:
        from app.views.webhook import webhook_bp
        app.register_blueprint(webhook_bp)
        logging.info("Webhook blueprint registrado")
    except ImportError as e:
        logging.error(f"Error importando webhook blueprint: {str(e)}")
    
    try:
        from app.views.health import health_bp
        app.register_blueprint(health_bp)
        logging.info("Health blueprint registrado")
    except ImportError as e:
        logging.error(f"Error importando health blueprint: {str(e)}")
    
    try:
        from app.views.dashboard import dashboard_bp
        app.register_blueprint(dashboard_bp)
        logging.info("Dashboard blueprint registrado")
    except ImportError as e:
        logging.error(f"Error importando dashboard blueprint: {str(e)}")
    
    logging.info("Proceso de registro de blueprints completado")