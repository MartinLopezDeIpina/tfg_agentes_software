# Guía de Onboarding

Bienvenido al proyecto IA Core Tools. Esta guía te ayudará a familiarizarte rápidamente con el proyecto, su estructura y los procesos de trabajo del equipo.

## Introducción al Proyecto

IA Core Tools es una plataforma interna de LKS Next diseñada para crear, configurar y desplegar agentes de IA basados en técnicas de Retrieval-Augmented Generation (RAG). La plataforma permite a equipos internos desarrollar soluciones de IA adaptadas a diferentes necesidades empresariales, integrando grandes modelos de lenguaje con repositorios de conocimiento personalizados.

## Primeros Pasos

### 1. Acceso a Recursos

Para comenzar, necesitarás acceso a:

- **Cuenta de Gitlab de LKS NEXT**: Necesitarás una cuenta de GitLab proporcionada por LKS NEXT para poder acceder al repositorio.
- **Conexión VPN**: Necesitarás estar conectado a la red privada virtual de LKS Next para poder acceder al repositorio. Conectate a la url: https://ssl.lks.es:8443/
- **Permisos de repositorio **: Solicita acceso al repositorio GitLab del proyecto
- **Documentación en Confluence**: Pide acceso a la documentación técnica del frontend
- **Google Drive compartido**: Para acceder a maquetas y recursos de diseño
- **Canales de comunicación**: Chats de Gmail y Microsoft Teams utilizados por el equipo

Contacta a Aritz Galdos (Desarrollador Líder) para obtener estos accesos.

### 2. Configuración del Entorno de Desarrollo

#### Requisitos Previos

- Python 3.11 o superior
- PostgreSQL con extensión pgvector
- Docker y Docker Compose (recomendado)
- Git

#### Instalación y Configuración

1. Clona el repositorio:
   ```bash
   git clone [URL_DEL_REPOSITORIO]
   cd ia-core-tools
   ```

2. Configura el entorno virtual:
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   pip install -r app/requirements.txt
   ```

3. Crea un archivo `.env` con las siguientes variables:
   ```
   SQLALCHEMY_DATABASE_URI=postgresql://iacore:iacore@postgres:5432/iacore
   OPENAI_API_KEY=tu_api_key
   ANTHROPIC_API_KEY=tu_api_key
   REPO_BASE_FOLDER=ruta_para_almacenar_documentos
   ```

4. Opción A - Desarrollo con Docker:
   ```bash
   docker-compose up -d
   ```

   Opción B - Desarrollo local:
   ```bash
   # Iniciar PostgreSQL localmente
   # Ejecutar migraciones
   alembic upgrade head
   # Iniciar la aplicación
   cd app && flask run
   ```

5. Accede a la aplicación en `http://localhost:5000`

## Estructura del Proyecto

Familiarízate con la estructura general del proyecto:

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

## Componentes Principales

### 1. Estructura de Datos

La aplicación se organiza en torno a estos conceptos clave:

- **App**: Contenedor principal que agrupa agentes y repositorios
- **Agent**: Configuración de un asistente de IA con prompt system y modelo
- **Repository**: Colección de documentos/recursos para RAG
- **Resource**: Documento individual (PDF) cargado y procesado
- **Model**: Configuración de modelos LLM disponibles (OpenAI, Anthropic)

### 2. Blueprints de Flask

El código está organizado en blueprints:

- `agents_blueprint`: Gestión de agentes de IA
- `repositories_blueprint`: Gestión de repositorios
- `resources_blueprint`: Gestión de recursos/documentos
- `api_blueprint`: Endpoints de API para interacción con agentes

### 3. Componentes RAG

El sistema RAG utiliza:

- `PGVectorTools`: Para gestión de vectores en PostgreSQL
- `modelTools`: Para interacción con modelos de lenguaje
- OpenAI Embeddings: Para vectorización de texto
- Langchain: Para componentes RAG (chains, retrievers, etc.)

## Flujos de Trabajo Principales

### 1. Flujo de Desarrollo

1. Selecciona un issue de GitHub para trabajar
2. Crea una rama específica para la tarea
3. Implementa los cambios siguiendo los estándares de código
4. Envía un Pull Request para revisión
5. Aplica comentarios y mejoras
6. Una vez aprobado, se fusionará a la rama principal

### 2. Flujo de la Aplicación

El flujo típico de la aplicación para usuarios:

1. Crear una aplicación
2. Crear repositorios y cargar documentos
3. Configurar agentes con prompts y modelos
4. Vincular agentes a repositorios para RAG
5. Probar agentes en el playground
6. Utilizar agentes en aplicaciones cliente

### 3. Flujo Frontend

Para tareas de frontend:

1. Consulta los diseños en Figma
2. Accede a las maquetas HTML en Google Drive
3. Adapta el HTML a plantillas Jinja2
4. Integra con rutas de Flask y datos dinámicos
5. Mantén la documentación actualizada en Confluence

## Reuniones y Comunicación

### Reuniones Clave

- **Reuniones Semanales**: Dirigidas por Aritz Galdos y Mikel Lonbide para revisar progreso y planificar
- **Reuniones Técnicas**: Según sea necesario para discutir desafíos específicos
- **Revisiones de Código**: A través de Pull Requests en GitHub

### Canales de Comunicación

- **Chats de Gmail**: Para comunicación rápida y consultas
- **Microsoft Teams**: Para reuniones virtuales y colaboración remota
- **Reuniones Presenciales**: En la oficina técnica de Zuatzu para colaboración intensiva
- **GitHub Issues**: Para seguimiento de tareas y reportes de problemas

## Resumen de Tecnologías

| Tecnología | Propósito |
|------------|-----------|
| Python | Lenguaje principal de backend |
| Flask | Framework web |
| SQLAlchemy | ORM para base de datos |
| PostgreSQL + pgvector | Base de datos con soporte vectorial |
| Langchain | Framework para RAG |
| OpenAI API | Modelos GPT-4o y embeddings |
| Anthropic API | Modelos Claude |
| Docker | Contenedorización |
| Alembic | Migraciones de base de datos |
| Jinja2 | Motor de plantillas |
| Bootstrap | Framework CSS |
| jQuery | Biblioteca JavaScript |

## Recursos de Aprendizaje

Para familiarizarte con las tecnologías utilizadas:

- **Flask**: [Documentación oficial](https://flask.palletsprojects.com/)
- **SQLAlchemy**: [Tutorial](https://docs.sqlalchemy.org/en/latest/tutorial/)
- **pgvector**: [GitHub Repository](https://github.com/pgvector/pgvector)
- **Langchain**: [Documentación](https://python.langchain.com/docs/get_started/introduction)
- **RAG (Retrieval-Augmented Generation)**: [OpenAI Cookbook](https://github.com/openai/openai-cookbook/blob/main/examples/retrieval_augmented_generation.ipynb)

## Documentación Adicional

Esta guía es un punto de partida. Para información más detallada, consulta:

1. [Equipo y Comunicación](./equipo-y-comunicacion.md) - Información sobre el equipo y canales de comunicación
2. [Metodología](./metodologia.md) - Metodología de trabajo y procesos
3. [Guía de Contribución](./guia-contribucion.md) - Instrucciones detalladas para contribuir
4. [Sistema de Gestión de Tareas](./sistema-gestion-tareas.md) - Gestión de issues y tareas
5. [Estándares de Código](./estandares-codigo.md) - Estándares y mejores prácticas
6. [Arquitectura de Software](./arquitectura-software.md) - Arquitectura detallada
7. [Flujos de Trabajo](./flujos-trabajo.md) - Flujos de trabajo detallados
8. [Despliegue](./despliegue.md) - Guía de despliegue
9. [Referencias Técnicas](./referencias-tecnicas.md) - Referencias técnicas adicionales

## Contactos Clave

- **Aritz Galdos**: Desarrollador Líder / Gestor del Proyecto
- **Mikel Lonbide**: Desarrollador Principal
- **Raúl**: Contribuidor
- **Juanjo**: Contribuidor

Si tienes preguntas o necesitas ayuda, no dudes en contactar a cualquiera de ellos a través de los canales de comunicación establecidos.

¡Bienvenido al equipo!
