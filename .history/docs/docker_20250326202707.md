# Despliegue con Docker

Este documento explica cómo desplegar el bot de WhatsApp utilizando Docker y Docker Compose.

## Requisitos previos

- [Docker](https://docs.docker.com/get-docker/) instalado
- [Docker Compose](https://docs.docker.com/compose/install/) instalado
- Un dominio estático de [ngrok](https://ngrok.com/) (recomendado para producción)

## Configuración

1. **Copiar el archivo de variables de entorno:**

   ```bash
   cp .env.example .env
   ```

2. **Editar el archivo `.env` con tus valores:**

   - Configurar las credenciales de WhatsApp Business API
   - Establecer la clave API de OpenAI y el ID del asistente
   - Configurar el token de autenticación de ngrok y el dominio

3. **Construir y levantar los contenedores:**

   ```bash
   docker-compose up -d
   ```

   Esto construirá los contenedores y los iniciará en segundo plano.

4. **Verificar que los servicios estén funcionando:**

   ```bash
   docker-compose ps
   ```

## Estructura de contenedores

Este despliegue incluye dos contenedores principales:

- **whatsapp-bot**: Servidor Flask que ejecuta el bot.
- **ngrok**: Expone el servidor Flask a internet con una URL accesible públicamente.

## Volúmenes persistentes

Se utilizan los siguientes volúmenes para garantizar la persistencia de datos:

- **./data**: Almacena datos de sesiones y threads.
- **./logs**: Almacena registros de la aplicación y conversaciones.

## Configuración de ngrok

Para usar un dominio estático de ngrok en producción:

1. Crear una cuenta en [ngrok.com](https://ngrok.com/)
2. Obtener un token de autenticación
3. [Crear un dominio estático](https://dashboard.ngrok.com/cloud-edge/domains)
4. Añadir estos valores al archivo `.env`

## Monitoreo

Se puede acceder a la interfaz web de ngrok en:

```
http://localhost:4040
```

Esta interfaz le permite inspeccionar las solicitudes entrantes y salientes, lo cual es útil para depuración.

## Verificación del estado

Para verificar el estado del servicio, puede acceder a:

```
http://localhost:8080/health
```

Este endpoint proporciona información sobre el estado de la aplicación, uso de recursos y configuración.

## Comandos útiles

- **Ver logs de los contenedores:**

  ```bash
  docker-compose logs -f
  ```

- **Reiniciar los servicios:**

  ```bash
  docker-compose restart
  ```

- **Detener los servicios:**

  ```bash
  docker-compose down
  ```

- **Reconstruir los contenedores (después de cambios en el código):**

  ```bash
  docker-compose up -d --build
  ```

## Solución de problemas

### El webhook no recibe mensajes

1. Verifique que ngrok esté funcionando correctamente accediendo a `http://localhost:4040`
2. Confirme que el dominio de ngrok está correctamente configurado en el panel de desarrollador de Meta
3. Verifique los logs de la aplicación con `docker-compose logs -f whatsapp-bot`

### La aplicación no responde

1. Verifique el estado de la aplicación con `http://localhost:8080/health`
2. Compruebe si hay errores en los logs con `docker-compose logs -f whatsapp-bot`
3. Reinicie la aplicación con `docker-compose restart whatsapp-bot`

### Problemas con ngrok

1. Verifique que el token de autenticación de ngrok sea válido
2. Compruebe que el dominio estático esté disponible y correctamente configurado
3. Reinicie el servicio ngrok con `docker-compose restart ngrok`