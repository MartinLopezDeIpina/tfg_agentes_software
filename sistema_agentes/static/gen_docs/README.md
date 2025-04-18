# LKS Next IA Core Tools

## Descripción

IA Core Tools es una plataforma interna de LKS Next destinada al desarrollo y gestión de aplicaciones de inteligencia artificial basadas en técnicas de Retrieval-Augmented Generation (RAG). La plataforma permite a los equipos internos de LKS Next crear, configurar y desplegar agentes de IA conectados a repositorios de conocimiento, facilitando la implementación de soluciones de IA avanzadas para diversos casos de uso empresarial.

El sistema implementa una interfaz web que permite:

- Gestionar aplicaciones y sus componentes
- Crear y configurar agentes de IA basados en modelos de OpenAI y Anthropic
- Gestionar repositorios de conocimiento mediante integración con bases de datos vectoriales
- Cargar y procesar documentos para entrenar los modelos de IA
- Probar los agentes en un entorno de "playground"

## Estructura de la Documentación

Esta documentación proporciona información detallada sobre todos los aspectos del proyecto IA Core Tools:

1. [Equipo y Comunicación](./equipo-y-comunicacion.md) - Información sobre el equipo, roles y canales de comunicación
2. [Metodología](./metodologia.md) - Detalles sobre la metodología de trabajo, ceremonias y procesos
3. [Guía de Contribución](./guia-contribucion.md) - Instrucciones detalladas para contribuir al proyecto
4. [Sistema de Gestión de Tareas](./sistema-gestion-tareas.md) - Información sobre cómo se gestionan las tareas
5. [Estándares de Código](./estandares-codigo.md) - Estándares de código y buenas prácticas
6. [Arquitectura de Software](./arquitectura-software.md) - Descripción detallada de la arquitectura del sistema
7. [Flujos de Trabajo](./flujos-trabajo.md) - Flujos detallados de trabajo
8. [Onboarding](./onboarding.md) - Guía de inicio para nuevos miembros del equipo
9. [Despliegue](./despliegue.md) - Guía de despliegue
10. [Referencias Técnicas](./referencias-tecnicas.md) - Referencias técnicas y documentación de soporte
11. [Información del Cliente](./informacion-cliente.md) - Información sobre el cliente y stakeholders

## Tecnologías Principales

- **Backend**: Python, Flask, SQLAlchemy
- **Base de Datos**: PostgreSQL con extensión pgvector
- **Vectorización**: OpenAIEmbeddings
- **Modelos de IA**: Integración con OpenAI (GPT-4o) y Anthropic (Claude)
- **Infraestructura**: Docker para despliegue y desarrollo

## Iniciar el Proyecto

### Requisitos Previos

- Python 3.11 o superior
- PostgreSQL con extensión pgvector
- Docker y Docker Compose (opcional)

### Configuración del Entorno

1. Clonar el repositorio:
   ```bash
   git clone [URL_DEL_REPOSITORIO]
   ```

2. Instalar dependencias:
   ```bash
   pip install -r app/requirements.txt
   ```

3. Configurar variables de entorno:
   ```bash
   # Crear archivo .env con las siguientes variables
   SQLALCHEMY_DATABASE_URI=postgresql://iacore:iacore@postgres:5432/iacore
   OPENAI_API_KEY=tu_api_key
   ANTHROPIC_API_KEY=tu_api_key
   REPO_BASE_FOLDER=ruta_para_almacenar_documentos
   ```

4. Iniciar la base de datos con Alembic:
   ```bash
   alembic upgrade head
   ```

5. Ejecutar la aplicación:
   ```bash
   cd app && flask run
   ```

### Iniciar con Docker

Alternativamente, puedes usar Docker Compose:

```bash
docker-compose up -d
```

## Licencia

Este proyecto está licenciado bajo LKS Inner Source License (LKSISL), una licencia específicamente diseñada para proyectos Inner Source dentro del grupo LKS Next.
