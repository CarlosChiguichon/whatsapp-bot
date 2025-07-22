"""
Integración con OpenAI utilizando la API de Chat Completions.
"""
import logging
import json
import os
import shelve
import openai
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar cliente de OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = "gpt-4-turbo"  # Usar el mejor modelo disponible, idealmente sería gpt-4o-mini
openai.api_key = OPENAI_API_KEY

def get_conversation_history(wa_id, max_messages=10):
    """
    Obtiene el historial de conversación de un usuario.
    
    Args:
        wa_id (str): ID de WhatsApp del usuario
        max_messages (int): Número máximo de mensajes a incluir
        
    Returns:
        list: Lista de mensajes para el contexto de la conversación
    """
    try:
        # Asegurar que exista el directorio para datos
        os.makedirs("data", exist_ok=True)
        
        # Intentar cargar el historial de conversación
        with shelve.open("data/conversations_db") as convo_shelf:
            history = convo_shelf.get(wa_id, [])
            
        # Limitar a los últimos max_messages mensajes para no exceder tokens
        return history[-max_messages:] if history else []
    except Exception as e:
        logging.error(f"Error al cargar historial de conversación: {str(e)}")
        return []

def store_conversation(wa_id, role, content):
    """
    Almacena un mensaje en el historial de conversación.
    
    Args:
        wa_id (str): ID de WhatsApp del usuario
        role (str): Rol del mensaje ('user' o 'assistant')
        content (str): Contenido del mensaje
    """
    try:
        # Asegurar que exista el directorio para datos
        os.makedirs("data", exist_ok=True)
        
        # Cargar historial existente
        with shelve.open("data/conversations_db") as convo_shelf:
            history = convo_shelf.get(wa_id, [])
            
            # Añadir nuevo mensaje
            history.append({"role": role, "content": content})
            
            # Guardar historial actualizado
            convo_shelf[wa_id] = history
    except Exception as e:
        logging.error(f"Error al guardar mensaje en historial: {str(e)}")

def get_system_prompt(name):
    """
    Genera el prompt del sistema para el asistente.
    
    Args:
        name (str): Nombre del usuario
        
    Returns:
        str: Prompt del sistema
    """
    return f"""Eres un asistente virtual de WhatsApp para Operadores Nacionales, una empresa del sector de energía solar.

INSTRUCCIONES PRINCIPALES:
- Ayuda a los clientes con consultas generales sobre energía solar y los servicios de la empresa.
- Si detectas que el cliente necesita soporte técnico o tiene un problema, el sistema automáticamente le enviará un formulario especializado.
- Solo responde consultas relacionadas con el negocio de energía solar y los productos de la empresa.
- Sé amable, profesional y conciso en tus respuestas.

PROTOCOLO DE CONVERSACIÓN:
- En tu primer mensaje, saluda al cliente por su nombre ({name}) y agradécele por contactar a Operadores Nacionales.
- Menciona el nombre de la empresa (Operadores Nacionales) solo en el primer mensaje y al finalizar la conversación.
- Si el cliente pregunta sobre productos o servicios, proporciona información general y sugiérele contactar al equipo comercial.

Al finalizar la conversación, agradece al cliente por contactar y menciona nuevamente el nombre de la empresa.

Estás hablando con {name} a través de WhatsApp. Mantén tus mensajes breves y directos.
"""

def detect_ticket_intent(message):
    """
    Detecta si el mensaje indica intención de crear un ticket.
    
    Args:
        message (str): Mensaje del usuario
        
    Returns:
        bool: True si se detecta intención de ticket, False en caso contrario
    """
    ticket_keywords = [
        "problema", "error", "falla", "ticket", "ayuda", "soporte", "no funciona",
        "issue", "bug", "help", "support", "not working", "broken", "doesn't work",
        "reportar", "reporte", "report", "queja", "complaint", "asistencia técnica",
        "mal funcionamiento", "avería", "servicio técnico", "reparación"
    ]
    
    message_lower = message.lower()
    
    for keyword in ticket_keywords:
        if keyword in message_lower:
            return True
            
    return False


def generate_ai_response(message_body, wa_id, name):
    """
    Genera una respuesta utilizando la API de Chat Completions de OpenAI.
    
    Args:
        message_body (str): Mensaje del usuario
        wa_id (str): ID de WhatsApp del usuario
        name (str): Nombre del usuario
        
    Returns:
        str: Respuesta generada
    """
    try:
        # Verificar configuración
        if not OPENAI_API_KEY:
            logging.error("API Key de OpenAI no configurada")
            return "Lo siento, el servicio de IA no está configurado correctamente."
        
        # Detectar intención de ticket
        if detect_ticket_intent(message_body):
            # Si se detecta intención de ticket, informar al controlador de WhatsApp
            logging.info(f"Intención de ticket detectada para {name}")
            
            # Devolver None para que el controlador maneje la creación del ticket
            # Nota: En la implementación actual, el módulo whatsapp.py debe manejar este caso
            return "Parece que necesitas ayuda con un problema técnico. Me gustaría crear un ticket de soporte para que nuestro equipo pueda asistirte. Por favor, proporciona un breve título que describa el problema:"
        
        # Obtener historial de conversación y añadir el mensaje actual
        conversation_history = get_conversation_history(wa_id)
        
        # Determinar si es primera interacción para ajustar el saludo
        is_first_interaction = len(conversation_history) == 0
        
        # Crear mensajes para la API de Chat Completions
        messages = [
            {"role": "system", "content": get_system_prompt(name)}
        ]
        
        # Añadir historial de conversación
        for msg in conversation_history:
            messages.append(msg)
            
        # Añadir mensaje actual del usuario
        messages.append({"role": "user", "content": message_body})
        
        # Añadir contexto adicional si es necesario
        if is_first_interaction:
            messages.append({
                "role": "system", 
                "content": "Esta es la primera interacción con este cliente. Asegúrate de presentarte en nombre de Operadores Nacionales."
            })
        
        # Llamar a la API de Chat Completions
        logging.info(f"Enviando solicitud a OpenAI para {name}")
        response = openai.ChatCompletion.create(
            model=MODEL,
            messages=messages,
            max_tokens=500,
            temperature=0.7,
        )
        
        # Extraer respuesta
        assistant_response = response.choices[0].message['content'].strip()
        
        # Guardar mensajes en historial
        store_conversation(wa_id, "user", message_body)
        store_conversation(wa_id, "assistant", assistant_response)
        
        return assistant_response
        
    except Exception as e:
        logging.error(f"Error al generar respuesta con IA: {str(e)}")
        return "Lo siento, estoy experimentando dificultades técnicas. Por favor, intenta de nuevo más tarde o contáctanos directamente al teléfono de soporte."