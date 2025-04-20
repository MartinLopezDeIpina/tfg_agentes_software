# Estándares de Código

Este documento establece los estándares de código y buenas prácticas para el proyecto IA Core Tools, basados en el código existente y las mejores prácticas de la industria.

## Estándares Generales

### Estructura del Proyecto

La estructura del proyecto debe mantenerse organizada y coherente:

```
ia-core-tools/
├── alembic/                 # Migraciones de base de datos
├── app/
│   ├── api/                 # Endpoints de API REST
│   ├── db/                  # Configuración de base de datos
│   ├── model/               # Modelos SQLAlchemy
│   ├── static/              # Archivos estáticos (CSS, JS, imágenes)
│   ├── templates/           # Plantillas HTML con Jinja2
│   ├── tools/               # Utilidades y herramientas
│   ├── views/               # Rutas de Flask (Blueprints)
│   ├── app.py               # Aplicación principal
│   └── extensions.py        # Extensiones de Flask
├── docs/                    # Documentación
├── notebooks/               # Cuadernos Jupyter para experimentación
└── docker-compose.yaml      # Configuración de Docker
```

### Convenciones de Nomenclatura

- **Archivos y Directorios**: Utilizar nombres descriptivos en minúsculas, con guiones bajos para separar palabras (snake_case)
- **Clases**: CamelCase (primera letra en mayúscula)
- **Funciones y Variables**: snake_case (minúsculas con guiones bajos)
- **Constantes**: MAYÚSCULAS_CON_GUIONES_BAJOS
- **Blueprints de Flask**: nombre_blueprint (terminando en "_blueprint")
- **Modelos SQLAlchemy**: CamelCase, representando entidades singulares (ej. "User", no "Users")

## Estándares por Tecnología

### Python

#### Estilo de Código

- Seguir PEP 8 para el formato del código
- Utilizar 4 espacios para la indentación (no tabulaciones)
- Limitar las líneas a 79-100 caracteres
- Incluir docstrings en clases y funciones siguiendo PEP 257
- Separar funciones y clases con dos líneas en blanco
- Separar métodos dentro de una clase con una línea en blanco

#### Ejemplos de Docstrings

Basado en el código existente, como en `pgVectorTools.py`:

```python
def index_resource(resource):
    """Indexes a resource by loading its content, splitting it into chunks, and adding it to the pgvector table."""
    loader = PyPDFLoader(os.path.join(REPO_BASE_FOLDER, str(resource.repository_id), resource.uri), extract_images=False)
    pages = loader.load()
    text_splitter = CharacterTextSplitter(chunk_size=10, chunk_overlap=0)
    docs = text_splitter.split_documents(pages)
    # ...
```

#### Importaciones

Organizar las importaciones en el siguiente orden, con una línea en blanco entre grupos:

1. Bibliotecas estándar de Python
2. Bibliotecas de terceros
3. Importaciones locales de la aplicación

Ejemplo basado en `app.py`:

```python
from flask import Flask, render_template, session, request
from flask_restful import Api, Resource
from flask_session import Session
import os
import json
from datetime import timedelta, datetime
from dotenv import load_dotenv

from app.extensions import db
from app.model.app import App
from app.api.api import api_blueprint
from app.views.agents import agents_blueprint
# ...
```

#### Variables de Entorno

- Utilizar `python-dotenv` para manejar variables de entorno
- Definir valores por defecto para entornos de desarrollo
- Documentar todas las variables de entorno requeridas

```python
load_dotenv()
SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI")
```

### SQLAlchemy y Modelos

#### Definición de Modelos

Seguir la estructura establecida para los modelos:

```python
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey 
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Agent(Base):
    __tablename__ = 'Agent'
    agent_id = Column(Integer, primary_key=True)
    name = Column(String(255))
    description = Column(String(1000))
    # ...
    
    # Relaciones
    model = relationship('Model', foreign_keys=[model_id])
    repository = relationship('Repository', back_populates='agents', foreign_keys=[repository_id])
    # ...
```

#### Migraciones

- Utilizar Alembic para todas las migraciones de la base de datos
- Crear migraciones autogeneradas cuando sea posible
- Revisar y ajustar las migraciones antes de aplicarlas
- Documentar cambios significativos en los mensajes de migración

```bash
alembic revision --autogenerate -m "Descripción clara del cambio"
alembic upgrade head
```

### Flask

#### Blueprints

Organizar las rutas de la aplicación en blueprints según la funcionalidad:

```python
from flask import Blueprint, render_template

blueprint_name = Blueprint('blueprint_name', __name__)

@blueprint_name.route('/ruta', methods=['GET', 'POST'])
def funcion_vista():
    # Lógica de la vista
    return render_template('template.html')
```

#### Extensiones

Inicializar las extensiones de Flask en `extensions.py` y registrarlas en `app.py`:

```python
# extensions.py
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

# app.py
from app.extensions import db
db.init_app(app)
```

### HTML (Plantillas Jinja2)

#### Estructura de Plantillas

- Utilizar herencia de plantillas para mantener un diseño consistente
- Centralizar elementos comunes en plantillas base
- Seguir una estructura clara con bloques bien definidos

```html
{% include 'header.html' %}

<div class="row">
    <!-- Contenido específico de la página -->
</div>

{% include 'footer.html' %}
```

#### Contexto de Plantilla

Proporcionar datos claros y bien estructurados a las plantillas:

```python
@repositories_blueprint.route('/app/<app_id>/repositories', methods=['GET'])
def repositories(app_id):
    repos = db.session.query(Repository).filter(Repository.app_id == app_id).all()
    return render_template('repositories/repositories.html', repos=repos)
```

### JavaScript

#### Organización

- Mantener el JavaScript en archivos separados cuando sea posible
- Para scripts pequeños específicos de una página, incluirlos al final de la plantilla

```html
<script>
    $('#send-btn').click(function () {
        var question = $('#question').val();
        var agent_id = '{{agent.agent_id}}';
        // ...
    });
</script>
```

#### AJAX y API

Para interacciones con la API, utilizar fetch o jQuery.ajax con un formato consistente:

```javascript
fetch('/api', {
    method: 'POST',
    credentials: 'include',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({ question: question, agent_id: agent_id }),
})
.then(response => response.json())
.then(data => {
    // Manejar la respuesta
})
.catch(error => {
    console.error('Error:', error);
});
```

### Docker

#### Estructura del Dockerfile

Mantener un Dockerfile limpio y eficiente:

```dockerfile
# Base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy application files
COPY ./app /app/app
COPY ./alembic /app/alembic
COPY alembic.ini /app/alembic.ini

# Install dependencies
RUN apt-get update && apt-get install -y \
    pkg-config \
    libmariadb-dev \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r app/requirements.txt

# Expose port
EXPOSE 5000

# Environment variables
ENV SQLALCHEMY_DATABASE_URI='postgresql://iacore:iacore@postgres:5432/iacore'

# Command
CMD ["sh", "-c", "alembic upgrade head && cd app && flask run --host=0.0.0.0"]
```

#### Docker Compose

Configurar Docker Compose para facilitar el desarrollo y despliegue:

```yaml
version: '3.3'
services:
  ia-core-tools:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "5000:5000"
    environment:
      - SQLALCHEMY_DATABASE_URI=postgresql+psycopg://iacore:iacore@postgres:5432/iacore
    depends_on:
      - postgres
    networks:
      - app-network

  postgres:
    image: pgvector/pgvector:pg17
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
```

## Buenas Prácticas de Seguridad

### Gestión de Secretos

- No incluir secretos (contraseñas, API keys) directamente en el código
- Utilizar variables de entorno o sistemas de gestión de secretos
- Si se requieren valores por defecto para desarrollo, usar valores obviamente ficticios

```python
app.secret_key = os.getenv('SECRET_KEY', 'development-key-change-in-production')
```

### Validación de Entrada

- Validar todas las entradas del usuario
- Implementar mecanismos de escape para prevenir XSS
- Utilizar consultas parametrizadas para evitar SQL injection

### Gestión de Sesiones

Configurar adecuadamente las sesiones:

```python
SESSION_TYPE = 'filesystem'
PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
app.config.from_object(__name__)
Session(app)
```

## Patrones y Anti-patrones

### Patrones Recomendados

- **Repository Pattern**: Utilizado en la gestión de recursos y agentes
- **Blueprint Pattern**: Para organizar rutas de Flask
- **Dependency Injection**: Para inyectar dependencias como la base de datos
- **Factory Pattern**: Para crear instancias de objetos complejos

### Anti-patrones a Evitar

- **Código Duplicado**: Refactorizar funcionalidades comunes
- **Métodos Demasiado Largos**: Dividir en funciones más pequeñas y específicas
- **Acoplamiento Fuerte**: Minimizar dependencias directas entre componentes
- **Configuración Hardcodeada**: Utilizar variables de entorno o archivos de configuración

## Proceso de Revisión de Código

Para asegurar el cumplimiento de estos estándares:

1. Realizar auto-revisiones antes de enviar pull requests
2. Utilizar herramientas de linting como flake8 o pylint
3. Revisar el código mediante pull requests y code reviews
4. Proporcionar feedback constructivo y específico
5. Abordar todos los comentarios antes de la fusión
