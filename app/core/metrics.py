from prometheus_client import Counter, Histogram, Gauge, generate_latest
from flask import Response
import time

# Definir métricas
messages_received = Counter('whatsapp_messages_received', 'Total messages received', ['type'])
messages_sent = Counter('whatsapp_messages_sent', 'Total messages sent', ['status'])
tickets_created = Counter('odoo_tickets_created', 'Total tickets created', ['status'])
response_time = Histogram('whatsapp_response_time', 'Response time in seconds')
queue_size = Gauge('queue_size', 'Current queue size', ['queue_name'])
active_sessions = Gauge('whatsapp_active_sessions', 'Number of active sessions')
circuit_breaker_state = Gauge('circuit_breaker_state', 'Circuit breaker state', ['service'])

def track_time(metric):
    """Decorador para medir tiempo de ejecución."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                metric.observe(time.time() - start)
        return wrapper
    return decorator

def register_metrics(app):
    """Registra endpoint de métricas."""
    @app.route('/metrics')
    def metrics():
        # Actualizar métricas dinámicas
        if hasattr(app, 'queue_manager'):
            stats = app.queue_manager.get_queue_stats()
            for queue_name, queue_stats in stats.items():
                queue_size.labels(queue_name=queue_name).set(queue_stats['pending'])
                
        # Actualizar sesiones activas
        from app.core.session import session_manager
        active_sessions.set(len(session_manager.sessions))
        
        # Actualizar estados de circuit breakers
        if hasattr(app, 'circuit_breakers'):
            for name, cb in app.circuit_breakers.items():
                state_value = {'closed': 0, 'open': 1, 'half_open': 0.5}
                circuit_breaker_state.labels(service=name).set(
                    state_value.get(cb.state.value, -1)
                )
        
        return Response(generate_latest(), mimetype='text/plain')