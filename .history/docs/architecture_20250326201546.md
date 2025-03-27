# Arquitectura del Bot de WhatsApp

## Visión general

Este proyecto implementa un bot para WhatsApp que utiliza la API de WhatsApp Business Cloud para recibir y enviar mensajes. El bot incorpora inteligencia artificial mediante la integración con OpenAI Assistants, y permite la creación de tickets de soporte en Odoo.

## Estructura del proyecto

El proyecto sigue el patrón de diseño Flask Factory, que permite una mayor modularidad, facilita las pruebas y permite crear múltiples instancias de la aplicación si es necesario.

```
whatsapp-bot/
├── app/                       # Directorio principal de la aplicación
│   ├── __init__.py            # Inicialización de la aplicación Flask
│   ├── config.py              # Configuración centralizada
│   ├── views/                 # Endpoints de la API
│   ├── core/                  # Funcionalidades principales
│   ├── integrations/          # Integraciones con servicios externos
│   └── utils/                 # Utilidades generales
├── data/                      # Datos persistentes (sesiones, hilos)
├── logs/                      # Registros de conversaciones y eventos
├── docs/                      # Documentación adicional
├── run.py                     # Punto de entrada de la aplicación
└── ...                        # Otros archivos de configuración
```

## Componentes principales

### 1. API de Webhook (app/views/webhook.py)

Este componente maneja las solicitudes entrantes de la API de WhatsApp:

- **Verificación del webhook**: Responde a las solicitudes de verificación de Meta
- **Procesamiento de mensajes**: Recibe y procesa los mensajes entrantes
- **Validación de seguridad**: Verifica la firma de las solicitudes para garantizar su autenticidad

### 2. Gestión de sesiones (app/core/session.py)

Maneja el estado de las conversaciones con los usuarios:

- **Seguimiento de sesiones**: Mantiene el contexto de cada conversación
- **Expiración automática**: Cierra sesiones inactivas después de un tiempo
- **Persistencia**: Guarda y carga sesiones para mantener el estado entre reinicios

### 3. Integración con WhatsApp (app/integrations/whatsapp.py)

Gestiona la comunicación con la API de WhatsApp:

- **Envío de mensajes**: Envía respuestas a los usuarios
- **Procesamiento de mensajes**: Interpreta los diferentes tipos de mensajes entrantes
- **Flujos de conversación**: Implementa los diferentes flujos de diálogo

### 4. Integración con OpenAI (app/integrations/openai.py)

Proporciona la inteligencia artificial del bot:

- **Asistente de OpenAI**: Utiliza la API de OpenAI Assistants para generar respuestas
- **Gestión de hilos**: Mantiene hilos de conversación para cada usuario
- **Detección de intenciones**: Analiza las intenciones del usuario en los mensajes

### 5. Integración con Odoo (app/integrations/odoo.py)

Permite la creación de tickets de soporte:

- **Creación de tickets**: Envía información a Odoo para crear tickets
- **Flujo de tickets**: Implementa el proceso paso a paso para recopilar información

## Flujos de trabajo

### Procesamiento de mensajes

1. El usuario envía un mensaje a través de WhatsApp
2. Meta envía una solicitud webhook al endpoint `/webhook`
3. La aplicación verifica la firma de la solicitud
4. El mensaje se extrae y se procesa según su tipo
5. Se actualiza la sesión del usuario
6. Dependiendo del estado de la sesión y el contenido del mensaje:
   - Se genera una respuesta con IA (OpenAI)
   - Se procesa un paso en la creación de un ticket
   - Se ejecuta una acción específica (como cerrar la sesión)
7. La respuesta se envía al usuario mediante la API de WhatsApp

### Creación de tickets

1. Se detecta la intención de crear un ticket en el mensaje del usuario
2. El bot cambia el estado de la sesión a `TICKET_CREATION`
3. El bot guía al usuario a través de los siguientes pasos:
   - Solicitar un título para el ticket
   - Pedir una descripción detallada
   - Solicitar correo electrónico (opcional)
   - Confirmar los datos
4. Con la confirmación del usuario, se crea el ticket en Odoo
5. Se informa al usuario del resultado y se le ofrece ayuda adicional

## Seguridad

El sistema implementa varias medidas de seguridad:

- **Verificación de firmas**: Todas las solicitudes webhook se validan usando HMAC con SHA256
- **Sanitización de entradas**: Los datos de entrada se limpian para prevenir inyecciones
- **Timeouts y reintentos**: Manejo adecuado de errores de conexión
- **Validación de configuración**: Verificación de variables de entorno requeridas
- **Gestión de sesiones**: Control de timeouts y expiración de sesiones inactivas

## Mejoras futuras

- **Soporte para multimedia**: Procesar imágenes, audio y otros tipos de medios
- **Análisis de sentimiento**: Detectar la satisfacción del usuario
- **Integración con más servicios**: Conectar con más sistemas externos
- **Mejoras de escalabilidad**: Implementar una cola de mensajes
- **Dashboard de administración**: Interfaz para gestionar el bot