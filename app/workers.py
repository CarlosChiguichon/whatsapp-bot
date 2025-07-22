import logging
from app.integrations.whatsapp import process_message as original_process_message
from app.core.metrics import messages_received, response_time, track_time

@track_time(response_time)
def process_whatsapp_message(message_data):
    """Worker para procesar mensajes de WhatsApp."""
    try:
        # Actualizar métrica
        messages_received.labels(type=message_data.get('type', 'unknown')).inc()
        
        # Procesar mensaje
        original_process_message(message_data)
        
    except Exception as e:
        logging.error(f"Error procesando mensaje: {str(e)}")
        raise

def process_odoo_webhook(webhook_data):
    """Worker para procesar webhooks hacia Odoo."""
    try:
        webhook_type = webhook_data.get('type')
        
        if webhook_type == 'ticket':
            # Importar aquí para evitar dependencias circulares
            from app.integrations.odoo import create_ticket
            from app.core.metrics import tickets_created
            
            result = create_ticket(**webhook_data['data'])
            if result['success']:
                tickets_created.labels(status='success').inc()
            else:
                tickets_created.labels(status='failed').inc()
                
    except Exception as e:
        logging.error(f"Error procesando webhook Odoo: {str(e)}")
        raise