"""
Endpoint para verificar el estado de la aplicación.
"""
from flask import Blueprint, jsonify
import logging
import psutil
import os

health_bp = Blueprint("health", __name__)

@health_bp.route("/health", methods=["GET"])
def health_check():
    """
    Endpoint para verificar que la aplicación esté funcionando correctamente.
    Útil para healthchecks de Docker/Kubernetes.
    
    Returns:
        response: Estado de salud de la aplicación en formato JSON
    """
    try:
        # Verificar uso de recursos
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Verificar que directorios existan
        data_dir_exists = os.path.isdir('data')
        logs_dir_exists = os.path.isdir('logs')
        
        # Verificar variables de entorno críticas
        env_vars = {
            'ACCESS_TOKEN': bool(os.getenv('ACCESS_TOKEN')),
            'APP_SECRET': bool(os.getenv('APP_SECRET')),
            'VERIFY_TOKEN': bool(os.getenv('VERIFY_TOKEN'))
        }
        
        # Construir respuesta
        response = {
            'status': 'healthy',
            'memory': {
                'total': memory.total,
                'available': memory.available,
                'percent': memory.percent
            },
            'disk': {
                'total': disk.total,
                'free': disk.free,
                'percent': disk.percent
            },
            'filesystem': {
                'data_directory': data_dir_exists,
                'logs_directory': logs_dir_exists
            },
            'config': {
                'env_vars_set': env_vars
            }
        }
        
        # Determinar estado general
        if memory.percent > 95 or disk.percent > 95:
            response['status'] = 'warning'
            
        if not all(env_vars.values()):
            response['status'] = 'warning'
            
        return jsonify(response), 200
        
    except Exception as e:
        logging.error(f"Error en health check: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500