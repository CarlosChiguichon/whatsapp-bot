"""
Funciones y decoradores de seguridad para la aplicación.
"""
from functools import wraps
import logging
import hashlib
import hmac

from flask import request, jsonify, current_app

def validate_signature(payload, signature):
    """
    Valida la firma de un payload entrante contra la firma esperada.
    
    Args:
        payload (str): Payload como cadena de texto
        signature (str): Firma proporcionada en el encabezado
        
    Returns:
        bool: True si la firma es válida, False en caso contrario
    """
    if not payload or not signature:
        return False
        
    try:
        # Usar el APP_SECRET para generar un hash del payload
        expected_signature = hmac.new(
            bytes(current_app.config["APP_SECRET"], "latin-1"),
            msg=payload.encode("utf-8"),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        # Comparar las firmas de manera segura (evita timing attacks)
        return hmac.compare_digest(expected_signature, signature)
    except Exception as e:
        logging.error(f"Error al validar firma: {str(e)}")
        return False

def signature_required(func):
    """
    Decorador que verifica la firma de las solicitudes entrantes.
    
    Args:
        func: Función a decorar
        
    Returns:
        function: Función decorada que verificará la firma
    """
    @wraps(func)
    def decorated_function(*args, **kwargs):
        # Extraer la firma del encabezado (quitar el prefijo 'sha256=')
        signature_header = request.headers.get("X-Hub-Signature-256", "")
        if not signature_header or not signature_header.startswith("sha256="):
            logging.warning("Solicitud sin firma o formato de firma inválido")
            return jsonify({"status": "error", "message": "Firma requerida"}), 401
            
        signature = signature_header[7:]  # Quitar 'sha256='
        
        # Validar la firma
        if not validate_signature(request.data.decode("utf-8"), signature):
            logging.warning("Verificación de firma fallida")
            return jsonify({"status": "error", "message": "Firma inválida"}), 403
            
        # Si la firma es válida, continuar con la función original
        return func(*args, **kwargs)
        
    return decorated_function