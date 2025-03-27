"""
Integración con la API de OpenAI Assistants.
"""
import logging
import time
import json
import os
import shelve
from openai import OpenAI
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar cliente de OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID")
client = OpenAI(api_key=OPENAI_API_KEY)

def check_if_thread_exists(wa_id):
    """
    Verifica si existe un hilo de conversación para el usuario.
    
    Args:
        wa_id (str): ID de WhatsApp del usuario
        
    Returns:
        str or None: ID del hilo si existe, None en caso contrario
    """
    try:
        with shelve.open("data/threads_db") as threads_shelf:
            return threads_shelf.get(wa_id, None)
    except Exception as e:
        logging.error(f"Error al verificar hilo existente: {str(e)}")
        return None

def store_thread(wa_id, thread_id):
    """
    Almacena el ID del hilo de conversación para un usuario.
    
    Args:
        wa_id (str): ID de WhatsApp del usuario
        thread_id (str): ID del hilo de conversación
    """
    try:
        with shelve.open("data/threads_db", writeback=True) as threads_shelf:
            threads_shelf[wa_id] = thread_id
            logging.info(f"Hilo {thread_id} almacenado para usuario {wa_id}")
    except Exception as e:
        logging.error(f"Error al almacenar hilo: {str(e)}")

def detect_intent(message, context=None):
    """
    Utiliza OpenAI para detectar intenciones del usuario.
    
    Args:
        message (str): Mensaje del usuario
        context (dict, optional): Contexto adicional
        
    Returns:
        str: Intención detectada
    """
    try:
        prompt = f"""
        Analiza el siguiente mensaje y determina la intención principal del usuario.
        
        Mensaje: {message}
        
        Posibles intenciones:
        - greeting: Saludo o inicio de conversación
        - support_request: Solicitud de ayuda técnica o soporte
        - information_request: Solicitud de información
        - complaint: Queja o reclamo
        - farewell: Despedida o cierre de conversación
        - other: Otra intención no listada
        
        Responde solo con el nombre de la intención.
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20,
            temperature=0.2
        )
        
        intent = response.choices[0].message.content.strip().lower()
        logging.info(f"Intención detectada: {intent}")
        return intent
        
    except Exception as e:
        logging.error(f"Error al detectar intención: {str(e)}")
        return "other"

def wait_for_run_completion(thread_id, run_id):
    """
    Espera a que se complete la ejecución del asistente.
    
    Args:
        thread_id (str): ID del hilo de conversación
        run_id (str): ID de la ejecución
        
    Returns:
        str: Contenido del mensaje más reciente
    """
    try:
        # Intentar hasta 30 segundos (60 intentos x 0.5 segundos)
        for _ in range(60):
            time.sleep(0.5)
            run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
            
            if run.status == "completed":
                # Obtener mensajes y devolver el más reciente
                messages = client.beta.threads.messages.list(thread_id=thread_id)
                if messages.data:
                    return messages.data[0].content[0].text.value
            
            elif run.status == "requires_action":
                logging.warning("La ejecución requiere acción pero ya estamos en el manejador")
                return "Lo siento, ha ocurrido un error al procesar tu solicitud."
            
            elif run.status in ["failed", "cancelled", "expired"]:
                error_msg = getattr(run, 'last_error', 'desconocido')
                logging.error(f"La ejecución falló con estado: {run.status}, error: {error_msg}")
                return "Lo siento, ha ocurrido un error al procesar tu solicitud."
                
        # Si se agota el tiempo
        logging.error("Timeout esperando la respuesta del asistente")
        return "Lo siento, estoy tardando demasiado en responder. Por favor, intenta más tarde."
        
    except Exception as e:
        logging.error(f"Error esperando la respuesta: {str(e)}")
        return "Lo siento, ha ocurrido un error al procesar tu solicitud."

def handle_function_call(thread_id, run_id, function_call, wa_id, name):
    """
    Maneja las llamadas a funciones del asistente.
    
    Args:
        thread_id (str): ID del hilo de conversación
        run_id (str): ID de la ejecución
        function_call: Objeto con información de la llamada a función
        wa_id (str): ID de WhatsApp del usuario
        name (str): Nombre del usuario
        
    Returns:
        str: Respuesta tras procesar la función
    """
    try:
        # Manejar la función create_odoo_ticket
        if function_call.name == "create_odoo_ticket":
            # Extraer argumentos
            args = json.loads(function_call.arguments)
            logging.info(f"Procesando creación de ticket para {name}: {args.get('subject', '')}")
            
            # Usar wa_id como teléfono si no se proporciona
            if not args.get("customer_phone"):
                args["customer_phone"] = wa_id
                
            # Usar name como nombre si no se proporciona
            if not args.get("customer_name"):
                args["customer_name"] = name
            
            # Importar aquí para evitar dependencia circular
            from app.integrations.odoo import create_ticket
            
            # Llamar a la función de creación de ticket
            result = create_ticket(
                customer_name=args.get("customer_name", name),
                customer_phone=args.get("customer_phone", wa_id),
                customer_email=args.get("customer_email", ""),
                subject=args.get("subject", ""),
                description=args.get("description", "")
            )
            
            # Enviar el resultado al asistente
            client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread_id,
                run_id=run_id,
                tool_outputs=[
                    {
                        "tool_call_id": function_call.id,
                        "output": json.dumps(result)
                    }
                ]
            )
            
            # Esperar a que el asistente procese el resultado
            return wait_for_run_completion(thread_id, run_id)
        
        # Para otras funciones que puedan añadirse en el futuro
        else:
            logging.warning(f"Llamada a función no soportada: {function_call.name}")
            return "Lo siento, no puedo procesar esa solicitud en este momento."
            
    except Exception as e:
        logging.error(f"Error al procesar la llamada a función: {str(e)}")
        
        try:
            # Informar del error al asistente
            error_result = {
                "success": False,
                "error": f"Error al procesar la solicitud: {str(e)}"
            }
            
            client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread_id,
                run_id=run_id,
                tool_outputs=[
                    {
                        "tool_call_id": function_call.id,
                        "output": json.dumps(error_result)
                    }
                ]
            )
            
            # Esperar respuesta actualizada
            return wait_for_run_completion(thread_id, run_id)
            
        except Exception as e2:
            logging.error(f"Error secundario al manejar error: {str(e2)}")
            return "Lo siento, ha ocurrido un error al procesar tu solicitud."

def run_assistant(thread, name, wa_id):
    """
    Ejecuta el asistente y maneja posibles llamadas a funciones.
    
    Args:
        thread: Objeto de hilo de conversación
        name (str): Nombre del usuario
        wa_id (str): ID de WhatsApp del usuario
        
    Returns:
        str: Respuesta del asistente
    """
    try:
        # Verificar que el ID del asistente esté configurado
        if not OPENAI_ASSISTANT_ID:
            logging.error("ID del asistente de OpenAI no configurado")
            return "Lo siento, el servicio de asistente no está configurado correctamente."
        
        # Obtener el asistente
        assistant = client.beta.assistants.retrieve(OPENAI_ASSISTANT_ID)
        
        # Ejecutar el asistente con instrucciones personalizadas
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id,
            instructions=f"Estás conversando con {name} a través de WhatsApp. Sé conciso en tus respuestas."
        )
        
        # Esperar hasta que se complete la ejecución o requiera acciones
        for _ in range(60):  # 30 segundos máximo
            time.sleep(0.5)
            run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            
            # Si la ejecución requiere acciones (llamadas a funciones)
            if run.status == "requires_action":
                tool_calls = run.required_action.submit_tool_outputs.tool_calls
                
                # Procesar cada llamada a función
                for tool_call in tool_calls:
                    if tool_call.type == "function":
                        function_call = tool_call.function
                        logging.info(f"Llamada a función detectada: {function_call.name}")
                        return handle_function_call(thread.id, run.id, function_call, wa_id, name)
            
            # Si se completa sin llamadas a funciones
            elif run.status == "completed":
                break
            
            # Si falla la ejecución
            elif run.status in ["failed", "cancelled", "expired"]:
                error_msg = getattr(run, 'last_error', 'desconocido')
                logging.error(f"La ejecución falló con estado: {run.status}, error: {error_msg}")
                return "Lo siento, ha ocurrido un error al procesar tu solicitud."
                
        # Si se completa normalmente, obtener el mensaje más reciente
        if run.status == "completed":
            messages = client.beta.threads.messages.list(thread_id=thread.id)
            if messages.data:
                new_message = messages.data[0].content[0].text.value
                logging.info(f"Mensaje generado: {new_message[:100]}...")
                return new_message
                
        # Si se agota el tiempo
        logging.error("Timeout esperando la respuesta del asistente")
        return "Lo siento, estoy tardando demasiado en responder. Por favor, intenta más tarde."
        
    except Exception as e:
        logging.error(f"Error al ejecutar el asistente: {str(e)}")
        return "Lo siento, ha ocurrido un error al procesar tu solicitud."

def generate_ai_response(message_body, wa_id, name):
    """
    Genera una respuesta utilizando el asistente de OpenAI.
    
    Args:
        message_body (str): Mensaje del usuario
        wa_id (str): ID de WhatsApp del usuario
        name (str): Nombre del usuario
        
    Returns:
        str: Respuesta generada por el asistente
    """
    try:
        # Verificar configuración
        if not OPENAI_API_KEY or not OPENAI_ASSISTANT_ID:
            logging.error("Configuración de OpenAI incompleta")
            return "Lo siento, el servicio de IA no está configurado correctamente."
            
        # Asegurar que exista el directorio para datos
        import os
        os.makedirs("data", exist_ok=True)
        
        # Verificar si existe un hilo para este usuario
        thread_id = check_if_thread_exists(wa_id)
        
        # Si no existe, crear uno nuevo
        if thread_id is None:
            logging.info(f"Creando nuevo hilo para {name} con wa_id {wa_id}")
            thread = client.beta.threads.create()
            store_thread(wa_id, thread.id)
            thread_id = thread.id
        else:
            # Recuperar el hilo existente
            logging.info(f"Recuperando hilo existente para {name} con wa_id {wa_id}")
            thread = client.beta.threads.retrieve(thread_id)
        
        # Añadir mensaje al hilo
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message_body,
        )
        
        # Ejecutar el asistente y obtener la respuesta
        new_message = run_assistant(thread, name, wa_id)
        return new_message
        
    except Exception as e:
        logging.error(f"Error al generar respuesta con IA: {str(e)}")
        return "Lo siento, estoy experimentando dificultades técnicas. Por favor, intenta de nuevo más tarde."