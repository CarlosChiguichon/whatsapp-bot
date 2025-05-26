# Stub mínimo para evitar errores
class QueueManager:
    def __init__(self, redis_url=None):
        self.redis_client = None
    
    def register_processor(self, queue_name, processor):
        pass
    
    def enqueue(self, queue_name, message, priority=5):
        # Procesar directamente sin cola
        pass
    
    def start_workers(self, queues):
        pass
    
    def get_queue_stats(self):
        return {}

class RateLimiter:
    def __init__(self, redis_client):
        pass