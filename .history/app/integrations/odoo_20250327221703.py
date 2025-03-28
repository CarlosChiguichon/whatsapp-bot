"""
Integración con Odoo para la creación de tickets de soporte.
"""
import requests
import json
import os
import logging
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def create_ticket(customer_name, customer_phone, customer_email, subject, description, country_id=None, serial_no=None, segment_id=None):
    """
    Crea un ticket de soporte en Odoo a través del webhook configurado.
    
    Args:
        customer_name (str): Nombre del cliente
        customer_phone (str): Número de teléfono del cliente
        customer_email (str): Correo electrónico del cliente
        subject (str): Asunto o título del ticket
        description (str): Descripción detallada del problema
        country_id (int, optional): ID del país del proyecto
        serial_no (str, optional): Número de serie del equipo
        segment_id (int, optional): ID del segmento de mercado
        
    Returns:
        dict: Respuesta del webhook de Odoo o mensaje de error
    """
    # Obtener la URL del webhook desde las variables de entorno
    odoo_webhook_url = os.getenv("ODOO_WEBHOOK_URL_TICKETS")
    
    if not odoo_webhook_url:
        logging.error("Variable de entorno ODOO_WEBHOOK_URL_TICKETS no configurada")
        return {
            "success": False,
            "error": "URL del webhook de Odoo no configurada"
        }
    
    # Validar datos de entrada
    if not description:
        logging.error("Datos de ticket incompletos: falta descripción")
        return {
            "success": False,
            "error": "La descripción es obligatoria"
        }
    
    if not customer_email:
        logging.error("Datos de ticket incompletos: falta correo electrónico")
        return {
            "success": False,
            "error": "El correo electrónico es obligatorio"
        }
    
    # Preparar el payload según el formato requerido por Odoo
    payload = {
        "team_id": 1,  # ID del equipo de soporte
        "name": subject,
        "partner_name": customer_name,
        "partner_phone": customer_phone,
        "partner_email": customer_email,
        "description": description
    }
    
    # Añadir campos opcionales si están disponibles
    if country_id:
        payload["country_id"] = country_id
        logging.info(f"Incluyendo país ID: {country_id} en el ticket")
    
    if serial_no:
        payload["serial_no"] = serial_no
        logging.info(f"Incluyendo número de serie: {serial_no} en el ticket")
    
    if segment_id:
        payload["segment_id"] = segment_id
        logging.info(f"Incluyendo segmento ID: {segment_id} en el ticket")
    
    # Configurar headers
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    try:
        # Enviar la solicitud al webhook de Odoo
        logging.info(f"Enviando ticket a Odoo: {subject}")
        logging.info(f"Payload del ticket: {json.dumps(payload)}")
        
        response = requests.post(
            odoo_webhook_url,
            data=json.dumps(payload),
            headers=headers,
            timeout=15  # 15 segundos de timeout
        )
        
        # Verificar si la solicitud fue exitosa
        if response.status_code in [200, 201]:
            logging.info(f"Ticket creado exitosamente en Odoo: {subject}")
            return {
                "success": True,
                "message": "Ticket creado exitosamente",
                "data": response.json() if response.text else {}
            }
        else:
            logging.error(f"Error al crear ticket en Odoo. Status: {response.status_code}, Respuesta: {response.text}")
            return {
                "success": False,
                "error": f"Error al crear ticket (código {response.status_code})",
                "details": response.text
            }
    
    except requests.Timeout:
        logging.error("Timeout al conectar con el webhook de Odoo")
        return {
            "success": False,
            "error": "Timeout al conectar con Odoo"
        }
    except requests.RequestException as e:
        logging.error(f"Error de conexión con Odoo: {str(e)}")
        return {
            "success": False,
            "error": f"Error de conexión: {str(e)}"
        }
    except Exception as e:
        logging.error(f"Error inesperado al crear ticket: {str(e)}")
        return {
            "success": False,
            "error": f"Error inesperado: {str(e)}"
        }

def create_lead(contact_name, mobile, email_from, country_id=None, segment_id=None, opportunity_mw=None):
    """
    Crea un lead comercial en Odoo a través del webhook configurado.
    
    Args:
        contact_name (str): Nombre del cliente
        mobile (str): Número de teléfono del cliente
        email_from (str): Correo electrónico del cliente
        country_id (int, optional): ID del país del proyecto
        segment_id (int, optional): ID del segmento de mercado
        opportunity_mw (float, optional): Tamaño del proyecto en MW
        
    Returns:
        dict: Respuesta del webhook de Odoo o mensaje de error
    """
    # Obtener la URL del webhook desde las variables de entorno
    odoo_webhook_url = os.getenv("ODOO_WEBHOOK_URL_LEADS")
    
    if not odoo_webhook_url:
        logging.error("Variable de entorno ODOO_WEBHOOK_URL_LEADS no configurada")
        return {
            "success": False,
            "error": "URL del webhook de Odoo para leads no configurada"
        }
    
    # Validar datos de entrada
    if not email_from:
        logging.error("Datos de lead incompletos: falta correo electrónico")
        return {
            "success": False,
            "error": "El correo electrónico es obligatorio"
        }
    
    # Generar el título del lead
    country_name = ""
    if country_id:
        from app.integrations.whatsapp import get_country_name_from_id
        country_name = get_country_name_from_id(country_id)
    
    name = f"{contact_name} - {country_name}"
    if opportunity_mw:
        name += f" - {opportunity_mw} MW"
    
    # Preparar el payload según el formato requerido por Odoo
    payload = {
        "type": "lead",
        "name": name,
        "contact_name": contact_name,
        "mobile": mobile,
        "email_from": email_from
    }
    
    # Añadir campos opcionales si están disponibles
    if country_id:
        payload["country_id"] = country_id
        logging.info(f"Incluyendo país ID: {country_id} en el lead")
    
    if segment_id:
        payload["market_segment_ids"] = segment_id
        logging.info(f"Incluyendo segmento ID: {segment_id} en el lead")
    
    if opportunity_mw:
        payload["opportunity_mw"] = opportunity_mw
        logging.info(f"Incluyendo tamaño del proyecto: {opportunity_mw} MW en el lead")
    
    # Configurar headers
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    try:
        # Enviar la solicitud al webhook de Odoo
        logging.info(f"Enviando lead a Odoo: {name}")
        logging.info(f"Payload del lead: {json.dumps(payload)}")
        
        response = requests.post(
            odoo_webhook_url,
            data=json.dumps(payload),
            headers=headers,
            timeout=15  # 15 segundos de timeout
        )
        
        # Verificar si la solicitud fue exitosa
        if response.status_code in [200, 201]:
            logging.info(f"Lead creado exitosamente en Odoo: {name}")
            return {
                "success": True,
                "message": "Lead creado exitosamente",
                "data": response.json() if response.text else {}
            }
        else:
            logging.error(f"Error al crear lead en Odoo. Status: {response.status_code}, Respuesta: {response.text}")
            return {
                "success": False,
                "error": f"Error al crear lead (código {response.status_code})",
                "details": response.text
            }
    
    except requests.Timeout:
        logging.error("Timeout al conectar con el webhook de Odoo")
        return {
            "success": False,
            "error": "Timeout al conectar con Odoo"
        }
    except requests.RequestException as e:
        logging.error(f"Error de conexión con Odoo: {str(e)}")
        return {
            "success": False,
            "error": f"Error de conexión: {str(e)}"
        }
    except Exception as e:
        logging.error(f"Error inesperado al crear lead: {str(e)}")
        return {
            "success": False,
            "error": f"Error inesperado: {str(e)}"
        }