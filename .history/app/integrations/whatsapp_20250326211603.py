"""
Integración con la API de WhatsApp Business Cloud.
"""
import logging
import json
import re
import requests
from flask import current_app

from app.core.session import session_manager
from app.integrations.openai import generate_ai_response
from app.integrations.odoo import create_ticket
from app.utils.helpers import process_text_for_whatsapp, log_conversation

# Configuración global para uso en hilos secundarios
whatsapp_config = {
    'access_token': None,
    'version': None,
    'phone_number_id': None
}

def init_whatsapp_config(app):
    """
    Inicializa la configuración de WhatsApp para uso fuera del contexto de Flask.
    
    Args:
        app (Flask): Instancia de la aplicación Flask
    """
    with app.app_context():
        whatsapp_config['access_token'] = app.config['ACCESS_TOKEN']
        whatsapp_config['version'] = app.config['VERSION']
        whatsapp_config['phone_number_id'] = app.config['PHONE_NUMBER_ID']
        
        # Configurar función de envío de mensajes en el gestor de sesiones
        session_manager.set_send_message_function(send_whatsapp_message)
        
        logging.info("Configuración de WhatsApp inicializada para hilos secundarios")

def send_whatsapp_message(recipient, text):
    """
    Envía un mensaje de WhatsApp a un destinatario.
    Esta función puede usarse desde hilos secundarios.
    
    Args:
        recipient (str): ID de WhatsApp del destinatario
        text (str): Contenido del mensaje
        
    Returns:
        dict or None: Respuesta de la API o None en caso de error
    """
    if not recipient or not text:
        logging.error("Receptor o texto de mensaje faltante")
        return None
        
    # Preparar el payload del mensaje
    data = json.dumps({
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "text",
        "text": {"preview_url": False, "body": text},
    })
    
    # Preparar los headers
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {whatsapp_config['access_token']}",
    }
    
    # URL de la API
    url = f"https://graph.facebook.com/{whatsapp_config['version']}/{whatsapp_config['phone_number_id']}/messages"
    
    try:
        # Enviar la solicitud
        response = requests.post(url, data=data, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Registrar respuesta
        logging.debug(f"Mensaje enviado a {recipient} - Status: {response.status_code}")
        return response
        
    except requests.Timeout:
        logging.error(f"Timeout al enviar mensaje a {recipient}")
        return None
    except requests.RequestException as e:
        logging.error(f"Error al enviar mensaje a {recipient}: {str(e)}")
        return None
    except Exception as e:
        logging.error(f"Error inesperado al enviar mensaje: {str(e)}")
        return None

def is_valid_message(body):
    """
    Verifica si el payload contiene un mensaje válido de WhatsApp.
    
    Args:
        body (dict): Cuerpo de la solicitud webhook
        
    Returns:
        bool: True si es un mensaje válido, False en caso contrario
    """
    try:
        return (
            body.get("object") and
            body.get("entry") and
            body["entry"][0].get("changes") and
            body["entry"][0]["changes"][0].get("value") and
            body["entry"][0]["changes"][0]["value"].get("messages") and
            body["entry"][0]["changes"][0]["value"]["messages"][0]
        )
    except (KeyError, IndexError, TypeError):
        return False

def extract_message_data(body):
    """
    Extrae los datos relevantes del mensaje de WhatsApp.
    
    Args:
        body (dict): Cuerpo de la solicitud webhook
        
    Returns:
        dict or None: Datos del mensaje o None si no es válido
    """
    try:
        if not is_valid_message(body):
            return None
            
        # Extraer ID de WhatsApp
        wa_id = body["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
        if not re.match(r"^\d+$", wa_id):  # Validar formato numérico
            logging.warning(f"ID de WhatsApp con formato inválido: {wa_id}")
            return None
            
        # Extraer nombre (con valor por defecto)
        try:
            name = body["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]
        except (KeyError, IndexError):
            name = "Usuario"
            
        # Extraer mensaje
        message = body["entry"][0]["changes"][0]["value"]["messages"][0]
        message_type = message.get("type", "unknown")
        
        # Procesar según el tipo de mensaje
        if message_type == "text":
            if "text" not in message or "body" not in message["text"]:
                return None
                
            message_body = message["text"]["body"]
            # Limitar longitud para prevenir ataques
            message_body = message_body[:1000]
            
            return {
                "wa_id": wa_id,
                "name": name,
                "type": "text",
                "body": message_body
            }
            
        elif message_type in ["image", "audio", "document", "video", "location"]:
            # Soporte básico para otros tipos de mensajes
            return {
                "wa_id": wa_id,
                "name": name,
                "type": message_type,
                "body": None,
                # Se podrían extraer más detalles específicos según el tipo
            }
            
        else:
            logging.warning(f"Tipo de mensaje no soportado: {message_type}")
            return None
            
    except Exception as e:
        logging.error(f"Error al extraer datos del mensaje: {str(e)}")
        return None

def detect_ticket_intent(message):
    """
    Detecta si el mensaje indica la intención de crear un ticket de soporte.
    
    Args:
        message (str): Texto del mensaje
        
    Returns:
        bool: True si se detecta intención de ticket, False en caso contrario
    """
    if not message:
        return False
        
    ticket_keywords = [
        "problema", "error", "falla", "ticket", "ayuda", "soporte", "no funciona",
        "issue", "bug", "help", "support", "not working", "broken", "doesn't work",
        "reportar", "reporte", "report", "queja", "complaint"
    ]
    
    message_lower = message.lower()
    
    for keyword in ticket_keywords:
        if keyword in message_lower:
            return True
            
    return False

def close_session_with_message(wa_id, name):
    """
    Cierra la sesión del usuario con un mensaje de despedida.
    
    Args:
        wa_id (str): ID de WhatsApp del usuario
        name (str): Nombre del usuario
    """
    farewell_message = f"Gracias por contactarnos, {name}. Tu sesión ha sido finalizada. Si necesitas ayuda adicional en el futuro, no dudes en escribirnos nuevamente. ¡Que tengas un excelente día!"
    
    # Enviar mensaje de despedida
    send_whatsapp_message(wa_id, farewell_message)
    
    # Registrar el mensaje en el historial antes de cerrar la sesión
    session_manager.add_message_to_history(wa_id, 'assistant', farewell_message)
    
    # Guardar conversación para análisis
    conversation = session_manager.get_message_history(wa_id)
    log_conversation(wa_id, conversation)
    
    # Cerrar la sesión
    session_manager.end_session(wa_id)
    logging.info(f"Sesión cerrada voluntariamente para {name} ({wa_id})")

def process_message(message_data):
    """
    Procesa un mensaje de WhatsApp y genera una respuesta.
    
    Args:
        message_data (dict): Datos del mensaje extraídos
    """
    # Extraer datos
    wa_id = message_data["wa_id"]
    name = message_data["name"]
    message_type = message_data["type"]
    
    # Obtener o crear sesión
    session = session_manager.get_session(wa_id)
    
    # Manejar diferentes tipos de mensajes
    if message_type == "text":
        message_body = message_data["body"]
        
        # Agregar mensaje al historial
        session_manager.add_message_to_history(wa_id, 'user', message_body)
        
        # Verificar si el usuario quiere finalizar la conversación
        if message_body.lower() in ['finalizar', 'terminar', 'cerrar', 'adios', 'chao', 'bye', 'end', 'fin', 'salir', 'exit']:
            close_session_with_message(wa_id, name)
            return
            
        # Procesar según el estado de la sesión
        if session['state'] == 'INITIAL' and message_body.lower() in ['hola', 'hi', 'hello']:
            # Mensaje de bienvenida
            response = f"¡Hola {name}! Bienvenido. ¿En qué puedo ayudarte hoy?"
            session_manager.update_session(wa_id, state='AWAITING_QUERY')
            
        elif session['state'] == 'AWAITING_RESPONSE_POST_TICKET':
            # Estado después de crear ticket
            if message_body.lower() in ['no', 'nop', 'nope', 'negativo', 'n']:
                close_session_with_message(wa_id, name)
                return
            else:
                response = "¿En qué más puedo ayudarte?"
                session_manager.update_session(wa_id, state='AWAITING_QUERY')
                
        elif session['state'] == 'TICKET_CREATION':
            # Proceso de creación de ticket
            response = handle_ticket_creation(wa_id, name, message_body, session)
            
        # Detectar intención de crear ticket
        elif detect_ticket_intent(message_body) and session['state'] != 'TICKET_CREATION':
            response = "Parece que necesitas ayuda con un problema. Me gustaría crear un ticket de soporte para que nuestro equipo pueda asistirte. Por favor, proporciona un breve título que describa el problema:"
            session_manager.update_session(
                wa_id, 
                state='TICKET_CREATION', 
                context={'ticket_step': 'subject'}
            )
            
        else:
            # Procesar con IA para otros mensajes
            try:
                # Importar aquí para evitar dependencia circular
                from app.integrations.openai import generate_ai_response
                response = generate_ai_response(message_body, wa_id, name)
            except Exception as e:
                logging.error(f"Error al procesar respuesta de IA: {str(e)}")
                response = "Lo siento, estoy experimentando dificultades técnicas en este momento. ¿Hay algo más en lo que pueda ayudarte?"
            
    else:
        # Respuesta para tipos de mensajes no soportados
        type_names = {
            "image": "imagen",
            "audio": "mensaje de voz",
            "document": "documento",
            "video": "video",
            "location": "ubicación"
        }
        type_name = type_names.get(message_type, message_type)
        
        # Agregar mensaje al historial
        session_manager.add_message_to_history(wa_id, 'user', f"[{type_name.upper()}]")
        
        response = f"He recibido tu {type_name}, pero actualmente no puedo procesar este tipo de contenido. ¿Podrías describir tu consulta en un mensaje de texto?"
    
    # Formatear respuesta para WhatsApp
    response = process_text_for_whatsapp(response)
    
    # Enviar respuesta
    send_whatsapp_message(wa_id, response)
    
    # Guardar respuesta en historial
    session_manager.add_message_to_history(wa_id, 'assistant', response)
    
    # Guardar sesiones periódicamente
    session_manager.save_sessions("data/sessions.json")

def handle_ticket_creation(wa_id, name, message_body, session):
    """
    Maneja el flujo de creación de un ticket de soporte.
    
    Args:
        wa_id (str): ID de WhatsApp del usuario
        name (str): Nombre del usuario
        message_body (str): Mensaje del usuario
        session (dict): Sesión del usuario
        
    Returns:
        str: Respuesta para el usuario
    """
    context = session['context']
    
    # Paso 1: Recopilar el asunto/título del ticket
    if 'ticket_step' not in context or context['ticket_step'] == 'subject':
        context['ticket_subject'] = message_body
        context['ticket_step'] = 'description'
        response = "Gracias. Por favor describe el problema en detalle."
    
    # Paso 2: Recopilar la descripción detallada
    elif context['ticket_step'] == 'description':
        context['ticket_description'] = message_body
        context['ticket_step'] = 'email'
        response = "Gracias por la información. Para poder dar seguimiento a tu caso, ¿podrías proporcionarme tu correo electrónico? (es importante agregarlo para darle un seguimiento apropiado). O responde 'omitir' si prefieres no compartirlo."
    
    # Paso 3: Solicitar email del cliente
    elif context['ticket_step'] == 'email':
        if message_body.lower() in ['no', 'n', 'paso', 'skip', 'omitir']:
            context['ticket_email'] = ""
        else:
            context['ticket_email'] = message_body
        
        context['ticket_step'] = 'confirmation'
        
        # Mostrar resumen y pedir confirmación
        email_info = f"*Email:* {context['ticket_email']}" if context['ticket_email'] else "*Email:* No proporcionado"
        response = (
            "Por favor, confirma los detalles del ticket:\n\n"
            f"*Asunto:* {context['ticket_subject']}\n"
            f"*Descripción:* {context['ticket_description']}\n"
            f"{email_info}\n\n"
            "¿Deseas crear este ticket? (responde 'sí' o 'no')"
        )
    
    # Paso 4: Confirmar y crear el ticket
    elif context['ticket_step'] == 'confirmation':
        if message_body.lower() in ['si', 'sí', 'yes', 'confirmar', 'aceptar', 'ok']:
            # Crear el ticket en Odoo
            ticket_result = create_ticket(
                customer_name=name,
                customer_phone=wa_id,
                customer_email=context.get('ticket_email', ""),
                subject=context['ticket_subject'],
                description=context['ticket_description']
            )
            
            if ticket_result.get('success', False):
                response = "¡Ticket creado con éxito! Un agente de soporte se pondrá en contacto contigo pronto. ¿Necesitas ayuda con algo más? (responde 'sí' o 'no')"
                # Cambiar a estado de espera post-ticket
                session_manager.update_session(wa_id, state='AWAITING_RESPONSE_POST_TICKET', context={})
            else:
                error_msg = ticket_result.get('error', 'Error desconocido')
                response = f"Lo siento, hubo un problema al crear el ticket: {error_msg}. Por favor, inténtalo más tarde o contacta directamente con soporte."
                # Restablecer el estado para nuevas consultas
                session_manager.update_session(wa_id, state='AWAITING_QUERY', context={})
        else:
            response = "Ticket cancelado. ¿En qué más puedo ayudarte?"
            # Restablecer el estado para nuevas consultas
            session_manager.update_session(wa_id, state='AWAITING_QUERY', context={})
    
    else:
        # Si por alguna razón el paso no está definido correctamente
        response = "Lo siento, hubo un problema con el proceso de creación del ticket. ¿Puedes intentarlo de nuevo?"
        session_manager.update_session(wa_id, state='AWAITING_QUERY', context={})
    
    # Actualizar el contexto si seguimos en creación de ticket
    if session['state'] == 'TICKET_CREATION':
        session_manager.update_session(wa_id, context=context)
        
    return response