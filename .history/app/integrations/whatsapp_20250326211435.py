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