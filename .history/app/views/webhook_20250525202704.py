import logging
import json
from flask import Blueprint, request, jsonify, current_app
from app.core.security import signature_required
from app.integrations.whatsapp import is_valid_message, extract_message_data, detect_ticket_intent
from app.core.metrics import messages_received

webhook_bp = Blueprint("webhook", __name__)

@webhook_bp.route("/webhook", methods=["GET"])
def verify_webhook():
    """Verificación del webhook de WhatsApp."""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    
    if not all([mode, token, challenge]):
        return jsonify({"status": "error", "message": "Parámetros incompletos"}), 400
    
    if mode == "subscribe" and token == current_app.config["VERIFY_TOKEN"]:
        logging.info("WEBHOOK_VERIFICADO")
        return challenge, 200
    else:
        return jsonify({"status": "error", "message": "Verificación fallida"}), 403

@webhook_bp.route("/webhook", methods=["POST"])
@signature_required
def webhook_handler():
    """Maneja webhooks encolando mensajes para procesamiento asíncrono."""
    try:
        body = request.get_json()
        if not body:
            return jsonify({"status": "error", "message": "Cuerpo inválido"}), 400
            
        # Ignorar actualizaciones de estado
        if (body.get("entry", [{}])[0]
            .get("changes", [{}])[0]
            .get("value", {})
            .get("statuses")):
            return jsonify({"status": "ok"}), 200
        
        # Extraer datos del mensaje
        message_data = extract_message_data(body)
        if not message_data:
            return jsonify({"status": "error", "message": "Formato inválido"}), 400
            
        # Determinar prioridad
        priority = 5  # Default
        if message_data.get("type") == "interactive_list":
            priority = 3  # Mayor prioridad para respuestas interactivas
        elif detect_ticket_intent(message_data.get("body", "")):
            priority = 4  # Prioridad alta para tickets
            
        # Encolar mensaje
        current_app.queue_manager.enqueue("whatsapp_incoming", message_data, priority)
        
        return jsonify({"status": "queued"}), 200
        
    except Exception as e:
        logging.error(f"Error en webhook: {str(e)}", exc_info=True)
        return jsonify({"status": "error"}), 500