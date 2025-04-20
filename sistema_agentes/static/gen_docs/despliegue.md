# Guía de Despliegue

Este documento describe los diferentes métodos para desplegar la aplicación IA Core Tools en entornos de desarrollo, pruebas y producción.

## Requisitos Previos

Independientemente del método de despliegue elegido, se requieren los siguientes componentes:

- PostgreSQL 13 o superior con la extensión pgvector instalada
- Acceso a las APIs de OpenAI y Anthropic (claves de API)
- Sistema de archivos para almacenar documentos
- Claves de API configuradas como variables de entorno

## Opciones de Despliegue

El proyecto IA Core Tools soporta dos métodos principales de despliegue:

1. **Despliegue Directo con Flask**: Para entornos de desarrollo o pequeñas implementaciones
2. **Despliegue con Docker**: Recomendado para entornos de prueba y producción

## 1. Despliegue Directo con Flask

### Configuración del Entorno

1. Clona el repositorio:
   ```bash
   git clone [URL_DEL_REPOSITORIO]
   cd ia-core-tools
   ```

2. Crea y activa un entorno virtual:
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```

3. Instala las dependencias:
   ```bash
   pip install -r app/requirements.txt
   ```

4. Configura las variables de entorno:
   ```bash
   # .env o exportar directamente
   export SQLALCHEMY_DATABASE_URI="postgresql://usuario:contraseña@host:puerto/nombre_db"
   export OPENAI_API_KEY="tu_clave_api_openai"
   export ANTHROPIC_API_KEY="tu_clave_api_anthropic"
   export REPO_BASE_FOLDER="/ruta/para/almacenar/documentos"
   ```

### Configuración de la Base de Datos

1. Asegúrate de que PostgreSQL esté instalado y en ejecución

2. Instala la extensión pgvector:
   ```bash
   # Conéctate a PostgreSQL
   psql -U usuario -d nombre_db
   
   # Instala la extensión
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

3. Ejecuta las migraciones de Alembic:
   ```bash
   alembic upgrade head
   ```

### Ejecución

Para iniciar la aplicación en modo desarrollo:

```bash
cd app
flask run --host=0.0.0.0 --port=5000
```

Para un entorno de producción, se recomienda usar Gunicorn:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 "app.app:app"
```

## 2. Despliegue con Docker

El proyecto incluye configuración de Docker para facilitar el despliegue en cualquier entorno.

### Usando docker-compose.yaml

1. Clona el repositorio:
   ```bash
   git clone [URL_DEL_REPOSITORIO]
   cd ia-core-tools
   ```

2. Configura las variables de entorno:
   
   Puedes modificar el archivo `docker-compose.yaml` para incluir tus variables de entorno:
   
   ```yaml
   ia-core-tools:
     environment:
       - SQLALCHEMY_DATABASE_URI=postgresql+psycopg://iacore:iacore@postgres:5432/iacore
       - OPENAI_API_KEY=tu_api_key
       - ANTHROPIC_API_KEY=tu_api_key
       - REPO_BASE_FOLDER=/app/uploads
   ```
   
   O crear un archivo `.env` en la raíz del proyecto:
   
   ```
   SQLALCHEMY_DATABASE_URI=postgresql+psycopg://iacore:iacore@postgres:5432/iacore
   OPENAI_API_KEY=tu_api_key
   ANTHROPIC_API_KEY=tu_api_key
   REPO_BASE_FOLDER=/app/uploads
   ```

3. Construye e inicia los contenedores:
   ```bash
   docker-compose up -d
   ```

   Esto iniciará tanto la aplicación Flask como PostgreSQL con pgvector.

4. Verifica los logs:
   ```bash
   docker-compose logs -f
   ```

### Usando la Imagen desde DockerHub

Alternativamente, puedes usar la imagen precompilada disponible en DockerHub:

```bash
# Crea un archivo docker-compose-dockerhub.yaml
docker-compose -f docker-compose-dockerhub.yaml up -d
```

Contenido del archivo `docker-compose-dockerhub.yaml`:
```yaml
version: '3.3'

services:
  ia-core-tools:
    image: aritzglks/lks-next-ia-core-tools:latest
    container_name: ia-core-tools
    ports:
      - "5000:5000"
    environment:
      - SQLALCHEMY_DATABASE_URI=postgresql://iacore:iacore@postgres:5432/iacore
      - OPENAI_API_KEY=CHANGE_ME
      - ANTHROPIC_API_KEY=CHANGE_ME
    depends_on:
      - postgres
    networks:
      - app-network

  postgres:
    image: postgres:13
    container_name: iacore_postgres
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_DB=iacore
      - POSTGRES_USER=iacore
      - POSTGRES_PASSWORD=iacore
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      app-network:
        aliases:
          - postgres

volumes:
  postgres-data:
    driver: local

networks:
  app-network:
    driver: bridge
```

## 3. Volúmenes y Persistencia

### Persistencia de Datos

Para garantizar la persistencia de los datos entre reinicios:

1. **Base de Datos**: 
   - En despliegue directo: Configurar PostgreSQL para mantener datos
   - En Docker: Usar volúmenes para la base de datos como se muestra en el docker-compose

2. **Archivos de Documentos**:
   - Configura `REPO_BASE_FOLDER` para apuntar a una ubicación persistente
   - En Docker: Monta un volumen para este directorio:
     ```yaml
     volumes:
       - ./uploads:/app/uploads
     ```

### Respaldo y Recuperación

Se recomienda configurar respaldos periódicos de:

1. **Base de Datos PostgreSQL**:
   ```bash
   pg_dump -U iacore -d iacore > backup_$(date +%Y%m%d).sql
   ```

2. **Directorio de documentos**:
   ```bash
   tar -czf documents_backup_$(date +%Y%m%d).tar.gz $REPO_BASE_FOLDER
   ```

## 4. Configuración para Producción

Para entornos de producción, se recomienda configurar:

### Seguridad

1. **Proxy Inverso**:
   - Configura Nginx o Apache como proxy inverso
   - Implementa HTTPS con certificados SSL/TLS
   - Configura cabeceras de seguridad adecuadas

2. **Variables de Entorno**:
   - Usa un gestor de secretos para las claves de API
   - No almacenes claves directamente en archivos de configuración

### Escalabilidad

Para aplicaciones con mayor carga:

1. **Múltiples Instancias**:
   - Despliega varias instancias detrás de un balanceador de carga
   - Usa entornos stateless y comparte solo la base de datos y el almacenamiento de archivos

2. **Redis para Sesiones**:
   - Configura Flask para usar Redis en lugar de sesiones de archivo:
   ```python
   from flask_session import Session
   app.config['SESSION_TYPE'] = 'redis'
   app.config['SESSION_REDIS'] = redis.from_url('redis://localhost:6379')
   Session(app)
   ```

## 5. Ajustes Post-Despliegue

Después del despliegue inicial:

1. **Migraciones de Base de Datos**:
   - Para actualizar el esquema después de cambios:
   ```bash
   # Directamente
   alembic upgrade head
   
   # Con Docker
   docker-compose exec ia-core-tools alembic upgrade head
   ```

2. **Cargar Datos Iniciales**:
   - El sistema carga automáticamente modelos de IA predefinidos a través de las migraciones de Alembic
   - Para cargar datos adicionales, usa las migraciones o scripts personalizados

## 6. Monitorización

Para monitorear la aplicación en producción:

1. **Logs**:
   - Configura la rotación de logs
   - Considera enviar logs a un sistema centralizado como ELK o Graylog

2. **Métricas**:
   - Implementa métricas básicas con Prometheus y Grafana
   - Monitorea uso de CPU, memoria, tiempo de respuesta y errores

## 7. Resolución de Problemas

Problemas comunes y soluciones:

| Problema | Posible Causa | Solución |
|----------|---------------|----------|
| Error de conexión a PostgreSQL | Base de datos no disponible o credenciales incorrectas | Verifica URL de conexión y credenciales |
| Error "No such file or directory" | `REPO_BASE_FOLDER` no existe o no tiene permisos | Crea el directorio y asigna permisos adecuados |
| Error de API de OpenAI/Anthropic | Clave de API incorrecta o límite excedido | Verifica la clave y los límites de la API |
| Vector extension not available | pgvector no instalado en PostgreSQL | Instala la extensión en la base de datos |

## 8. Ejemplo de Configuración Nginx

Para desplegar detrás de Nginx:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    # Redirecciona a HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    # Configuraciones SSL recomendadas
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 9. Actualizaciones y Mantenimiento

Para actualizar la aplicación:

1. **Con Despliegue Directo**:
   ```bash
   # Detén la aplicación actual
   # Actualiza el código desde el repositorio
   git pull
   
   # Actualiza dependencias
   pip install -r app/requirements.txt
   
   # Ejecuta migraciones
   alembic upgrade head
   
   # Reinicia la aplicación
   flask run # o gunicorn
   ```

2. **Con Docker**:
   ```bash
   # Actualiza el código
   git pull
   
   # Reconstruye y reinicia los contenedores
   docker-compose down
   docker-compose build
   docker-compose up -d
   ```

## Conclusión

Esta guía cubre los métodos principales para desplegar IA Core Tools. Selecciona el enfoque más adecuado según tus necesidades específicas y la infraestructura disponible.

Para entornos de desarrollo y pruebas, el despliegue directo con Flask o Docker son opciones viables. Para producción, se recomienda el enfoque basado en Docker con configuraciones adicionales de seguridad y escalabilidad.
