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
MODEL = "gpt-3.5-turbo"  # Modelo predeterminado, también funciona con gpt-4 si tienes acceso
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
    return f"""Eres un asistente virtual de WhatsApp, amable y servicial. 
Estás hablando con {name}.
Tus respuestas deben ser concisas y directas, ideales para mensajería móvil.
Evita respuestas extremadamente largas.

Si el usuario necesita crear un ticket de soporte, pregúntale por los detalles del problema.
Si el usuario se despide o indica que ha terminado, responde amablemente y finaliza la conversación.

Mantén un tono cordial pero profesional. Sé útil y proporciona información precisa.
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
        "reportar", "reporte", "report", "queja", "complaint"
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
            # Nota: En tu implementación actual, el módulo whatsapp.py debe manejar este caso
            # Como no podemos modificar whatsapp.py en este punto, retornamos un mensaje informativo
            return "Parece que necesitas ayuda con un problema. ¿Podrías describir el problema que estás experimentando?"
            
        # Obtener historial de conversación y añadir el mensaje actual
        conversation_history = get_conversation_history(wa_id)
        
        # Crear mensajes para la API de Chat Completions
        messages = [
            {"role": "system", "content": get_system_prompt(name)}
        ]
        
        # Añadir historial de conversación
        for msg in conversation_history:
            messages.append(msg)
            
        # Añadir mensaje actual del usuario
        messages.append({"role": "user", "content": message_body})
        
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
        return "Lo siento, estoy experimentando dificultades técnicas. Por favor, intenta de nuevo más tarde."