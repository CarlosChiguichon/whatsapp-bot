"""
Implementación básica de Circuit Breaker para manejar fallas de servicios externos.
"""
import logging
from datetime import datetime, timedelta
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    """
    Circuit Breaker básico para proteger contra fallas de servicios externos.
    """
    
    def __init__(self, name, failure_threshold=5, timeout=60):
        """
        Inicializa el Circuit Breaker.
        
        Args:
            name (str): Nombre del circuit breaker
            failure_threshold (int): Número de fallas antes de abrir el circuito
            timeout (int): Tiempo en segundos antes de intentar medio-abierto
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        
    def call(self, func, *args, **kwargs):
        """
        Ejecuta una función protegida por el circuit breaker.
        
        Args:
            func: Función a ejecutar
            *args, **kwargs: Argumentos para la función
            
        Returns:
            Resultado de la función
            
        Raises:
            CircuitBreakerOpenError: Si el circuito está abierto
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logging.info(f"Circuit breaker {self.name} en estado HALF_OPEN")
            else:
                raise CircuitBreakerOpenError(f"Circuit breaker {self.name} está abierto")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self):
        """Verifica si debería intentar resetear el circuito."""
        if self.last_failure_time is None:
            return True
        return datetime.now() - self.last_failure_time > timedelta(seconds=self.timeout)
    
    def _on_success(self):
        """Maneja una ejecución exitosa."""
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            logging.info(f"Circuit breaker {self.name} cerrado después de éxito")
    
    def _on_failure(self):
        """Maneja una falla."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logging.warning(f"Circuit breaker {self.name} abierto después de {self.failure_count} fallas")
    
    def get_status(self):
        """
        Obtiene el estado actual del circuit breaker.
        
        Returns:
            dict: Estado del circuit breaker
        """
        return {
            'name': self.name,
            'state': self.state.value,
            'failure_count': self.failure_count,
            'failure_threshold': self.failure_threshold,
            'last_failure_time': self.last_failure_time.isoformat() if self.last_failure_time else None
        }

class CircuitBreakerOpenError(Exception):
    """Excepción lanzada cuando el circuit breaker está abierto."""
    pass