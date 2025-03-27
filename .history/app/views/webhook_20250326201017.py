"""
Endpoints para la recepción de webhooks de WhatsApp.
"""
import logging
import json

from flask import Blueprint, request, jsonify, current_app

from app.core.security import signature_required
from app.integrations.whatsapp import process_message, is_valid_message, extract_message_data

# Crear blueprint para las rutas de webhook
webhook_bp = Blueprint("webhook", __name__)

@webhook_bp.route("/webhook", methods=["GET"])
def verify_webhook():
    """
    Maneja las solicitudes de verificación de webhook de WhatsApp.
    Esta es una verificación requerida por Meta para confirmar que somos dueños del endpoint.
    
    Returns:
        response: Una respuesta HTTP adecuada para la verificación
    """
    # Extraer parámetros de la solicitud de verificación
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    
    # Verificar que los parámetros existan
    if not all([mode, token, challenge]):
        logging.warning("Verificación incompleta: faltan parámetros")
        return jsonify({
            "status": "error", 
            "message": "Parámetros de verificación incompletos"
        }), 400
    
    # Verificar que los valores sean correctos
    if mode == "subscribe" and token == current_app.config["VERIFY_TOKEN"]:
        logging.info("WEBHOOK_VERIFICADO")
        return challenge, 200
    else:
        logging.warning(f"VERIFICACIÓN_FALLIDA: token={token}, mode={mode}")
        return jsonify({
            "status": "error", 
            "message": "Verificación fallida"
        }), 403

@webhook_bp.route("/webhook", methods=["POST"])
@signature_required
def webhook_handler():
    """
    Maneja las solicitudes POST entrantes desde la API de WhatsApp.
    La firma se verifica mediante el decorador @signature_required.
    
    Returns:
        response: Respuesta JSON con estado 200 si todo OK
    """
    try:
        # Obtener y validar el cuerpo de la solicitud
        body = request.get_json()
        if not body:
            logging.warning("Solicitud recibida sin cuerpo JSON válido")
            return jsonify({"status": "error", "message": "Cuerpo JSON inválido"}), 400
            
        # Verificar si es una actualización de estado (no un mensaje)
        if (body.get("entry", [{}])[0]
            .get("changes", [{}])[0]
            .get("value", {})
            .get("statuses")):
            logging.debug("Actualización de estado recibida")
            return jsonify({"status": "ok"}), 200
        
        # Validar y extraer datos del mensaje
        message_data = extract_message_data(body)
        if not message_data:
            logging.warning("Formato de mensaje inválido o no soportado")
            return jsonify({
                "status": "error", 
                "message": "Formato de mensaje inválido o no soportado"
            }), 400
            
        # Procesar el mensaje
        process_message(message_data)
        return jsonify({"status": "ok"}), 200
        
    except json.JSONDecodeError:
        logging.error("Error al decodificar JSON")
        return jsonify({"status": "error", "message": "JSON inválido"}), 400
    except Exception as e:
        logging.error(f"Error al procesar webhook: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": "Error interno del servidor"}), 500