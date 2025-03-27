"""
Funciones auxiliares para el bot de WhatsApp.
"""
import logging
import re
import json
import os
from datetime import datetime

def process_text_for_whatsapp(text):
    """
    Procesa el texto para ajustarlo al formato de WhatsApp.
    
    Args:
        text (str): Texto original
        
    Returns:
        str: Texto formateado para WhatsApp
    """
    if not text:
        return ""
        
    # Eliminar secciones entre corchetes (que pueden ser instrucciones internas)
    pattern = r"\【.*?\】"
    text = re.sub(pattern, "", text).strip()
    
    # Convertir negrita de markdown (**palabra**) a formato WhatsApp (*palabra*)
    pattern = r"\*\*(.*?)\*\*"
    replacement = r"*\1*"
    text = re.sub(pattern, replacement, text)
    
    # Limitar longitud para evitar problemas
    max_length = 4000  # WhatsApp tiene un límite aproximado de 4096 caracteres
    if len(text) > max_length:
        text = text[:max_length] + "..."
        
    return text

def log_conversation(user_id, conversation):
    """
    Guarda un registro de la conversación para análisis posterior.
    
    Args:
        user_id (str): ID del usuario
        conversation (list): Lista de mensajes de la conversación
    """
    try:
        # Crear directorio si no existe
        os.makedirs("logs", exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = {
            "user_id": user_id,
            "timestamp": timestamp,
            "messages": conversation
        }
        
        # Guardar en archivo JSON Lines
        with open("logs/conversations.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            
    except Exception as e:
        logging.error(f"Error al registrar conversación: {str(e)}")

def sanitize_input(text):
    """
    Sanitiza la entrada de texto para prevenir inyecciones.
    
    Args:
        text (str): Texto de entrada
        
    Returns:
        str: Texto sanitizado
    """
    if not text:
        return ""
        
    # Eliminar caracteres potencialmente peligrosos
    sanitized = re.sub(r"[^\w\s\.,;:¿?¡!@#$%^&*()-=+\[\]{}|<>\"\'`~/\\]", "", text)
    
    # Limitar longitud
    return sanitized[:1000]

def format_ticket_info(ticket):
    """
    Formatea la información de un ticket para mostrarla al usuario.
    
    Args:
        ticket (dict): Información del ticket
        
    Returns:
        str: Texto formateado
    """
    if not ticket:
        return "No hay información disponible sobre este ticket."
        
    formatted = (
        f"*Ticket #{ticket.get('id', 'N/A')}*\n"
        f"*Asunto:* {ticket.get('name', 'Sin asunto')}\n"
        f"*Estado:* {ticket.get('stage_name', 'Desconocido')}\n"
        f"*Fecha:* {ticket.get('create_date', 'N/A')}\n"
        f"*Equipo:* {ticket.get('team_name', 'Sin asignar')}"
    )
    
    if ticket.get('description'):
        formatted += f"\n\n*Descripción:*\n{ticket.get('description')}"
        
    return formatted

def extract_metrics():
    """
    Extrae métricas básicas de uso del bot.
    
    Returns:
        dict: Diccionario con métricas
    """
    try:
        from app.core.session import session_manager
        
        # Contar sesiones activas
        active_sessions = len(session_manager.sessions)
        
        # Analizar estados de las sesiones
        states = {}
        for user_id, session in session_manager.sessions.items():
            state = session.get('state', 'UNKNOWN')
            states[state] = states.get(state, 0) + 1
            
        # Contar tickets creados
        tickets_created = 0
        for user_id, session in session_manager.sessions.items():
            history = session.get('message_history', [])
            for msg in history:
                if msg.get('role') == 'assistant' and "ticket creado con éxito" in msg.get('content', '').lower():
                    tickets_created += 1
                    break
        
        return {
            "active_sessions": active_sessions,
            "session_states": states,
            "tickets_created": tickets_created,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Error al extraer métricas: {str(e)}")
        return {
            "error": "No se pudieron extraer métricas",
            "timestamp": datetime.now().isoformat()
        }