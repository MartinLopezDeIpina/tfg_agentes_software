# Referencias Técnicas

Este documento proporciona referencias técnicas detalladas y documentación de soporte para el proyecto IA Core Tools. Incluye información sobre las tecnologías utilizadas, bibliotecas principales, y recursos para profundizar en aspectos técnicos específicos.

## Tecnologías Principales

### Flask

Flask es el framework web utilizado para construir la aplicación. La estructura del proyecto sigue el patrón de organización recomendado por Flask, con blueprints para modularizar la aplicación.

- **Documentación oficial**: [Flask Documentation](https://flask.palletsprojects.com/)
- **Versión utilizada**: Ver en `app/requirements.txt`
- **Patrones implementados**:
  - Blueprints para modularización de rutas
  - Factory pattern para inicialización de la aplicación
  - Extensiones para funcionalidades adicionales

### SQLAlchemy y PostgreSQL

SQLAlchemy es el ORM (Object-Relational Mapping) utilizado para interactuar con la base de datos PostgreSQL.

- **Documentación SQLAlchemy**: [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- **Documentación PostgreSQL**: [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- **pgvector**: [pgvector GitHub](https://github.com/pgvector/pgvector) - Extensión para búsqueda vectorial en PostgreSQL

### Retrieval-Augmented Generation (RAG)

El proyecto implementa técnicas RAG para mejorar las respuestas de los modelos de lenguaje utilizando conocimiento específico.

- **Langchain**: [Langchain Documentation](https://python.langchain.com/docs/get_started/introduction) - Framework utilizado para implementar RAG
- **Introducción a RAG**: [OpenAI RAG Overview](https://platform.openai.com/docs/tutorials/building-with-rag)
- **Arquitecturas RAG avanzadas**: [Langchain RAG Patterns](https://python.langchain.com/docs/use_cases/question_answering/)

### Modelos de Lenguaje (LLMs)

El sistema se integra con modelos de OpenAI y Anthropic.

- **OpenAI API**: [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
  - Modelos disponibles: GPT-4o, GPT-4o-mini (ver `alembic/versions/a460ad150e9e_add_initial_models.py`)
- **Anthropic API**: [Anthropic API Reference](https://docs.anthropic.com/claude/reference/getting-started-with-the-api)
  - Modelos disponibles: Claude-3.5-sonnet, Claude-3-opus (ver `alembic/versions/a6d7ddf5f9ed_add_antrophic_models.py`)

### Docker

El proyecto incluye configuración Docker para facilitar el desarrollo y despliegue.

- **Docker Compose**: [Docker Compose Documentation](https://docs.docker.com/compose/)
- **Archivo de configuración**: `docker-compose.yaml` y `docker-compose-dockerhub.yaml`

## Componentes del Sistema

### Estructura de la Base de Datos

El esquema de la base de datos está definido en los modelos SQLAlchemy y las migraciones Alembic:

```
App
├── app_id (PK)
└── name

Repository
├── repository_id (PK)
├── name
├── type
├── status
└── app_id (FK -> App.app_id)

Resource
├── resource_id (PK)
├── name
├── uri
├── type
├── status
└── repository_id (FK -> Repository.repository_id)

Agent
├── agent_id (PK)
├── name
├── description
├── system_prompt
├── prompt_template
├── type
├── status
├── model_id (FK -> Model.model_id)
├── repository_id (FK -> Repository.repository_id)
├── app_id (FK -> App.app_id)
└── has_memory

Model
├── model_id (PK)
├── provider
├── name
└── description
```

### ModelTools (app/tools/modelTools.py)

Este componente gestiona la interacción con modelos de lenguaje:

```python
# Invocación básica de modelo
def invoke(agent, input):
    # Crea prompt a partir de plantilla
    # Invoca el modelo
    # Devuelve respuesta

# Invocación de modelo con RAG
def invoke_rag_with_repo(agent, input):
    # Convierte input a embedding
    # Busca documentos similares
    # Crea prompt con contexto
    # Invoca el modelo
    # Devuelve respuesta

# Invocación de modelo RAG con memoria conversacional
def invoke_ConversationalRetrievalChain(agent, input, session):
    # Configura memoria y retriever
    # Crea chain conversacional
    # Procesa input y devuelve respuesta
```

### PGVectorTools (app/tools/pgVectorTools.py)

Este componente gestiona la interacción con la base de datos vectorial:

```python
class PGVectorTools:
    # Inicialización con conexión a base de datos
    def __init__(self, db): ...
    
    # Crea tabla pgvector para un repositorio
    def create_pgvector_table(self, repository_id): ...
    
    # Indexa un recurso (documento)
    def index_resource(self, resource): ...
    
    # Elimina un recurso de la base de datos
    def delete_resource(self, resource): ...
    
    # Busca recursos similares por vector
    def search_similar_resources(self, repository_id, embed, RESULTS=5): ...
    
    # Crea retriever para RAG
    def get_pgvector_retriever(self, repository_id): ...
```

## APIs y Endpoints

### API REST

La aplicación expone una API REST para la interacción con agentes:

```
POST /api
{
    "question": "texto de la pregunta",
    "agent_id": "id numérico del agente"
}

Respuesta:
{
    "input": "pregunta original",
    "generated_text": "respuesta del modelo",
    "control": {
        "temperature": 0.8,
        "max_tokens": 100,
        ...
    },
    "metadata": {
        "model_name": "nombre del modelo",
        "timestamp": "2024-04-04T12:00:00Z"
    }
}
```

### Rutas Web

Las principales rutas de la aplicación web incluyen:

| Ruta | Función | Descripción |
|------|---------|-------------|
| `/` | `index` | Página principal con lista de aplicaciones |
| `/app/<app_id>` | `app_index` | Dashboard de una aplicación específica |
| `/app/<app_id>/agents` | `app_agents` | Gestión de agentes |
| `/app/<app_id>/repositories` | `repositories` | Gestión de repositorios |
| `/app/<app_id>/agent/<agent_id>/play` | `app_agent_playground` | Playground para probar un agente |

## Librerías y Dependencias

Las principales dependencias del proyecto están especificadas en `app/requirements.txt`:

```
flask                # Framework web
flask-sqlalchemy     # ORM para base de datos
flask-restful        # Soporte para API REST
Flask-Session        # Gestión de sesiones
langchain            # Framework para RAG
langchain-openai     # Integración con OpenAI
langchain-anthropic  # Integración con Anthropic
langchain-community  # Componentes comunitarios
langchain_postgres   # Integración con PostgreSQL/pgvector
psycopg2-binary      # Driver PostgreSQL
alembic              # Migraciones de base de datos
pypdf                # Procesamiento de archivos PDF
```

## Guías Técnicas

### Creación de un Nuevo Modelo LLM

Para añadir un nuevo modelo LLM al sistema:

1. Crear una migración Alembic:
   ```bash
   alembic revision -m "add_new_model"
   ```

2. Editar la migración para insertar el nuevo modelo:
   ```python
   def upgrade():
       op.bulk_insert(
           sa.table('Model',
               sa.column('provider', sa.String),
               sa.column('name', sa.String),
               sa.column('description', sa.String)
           ),
           [
               {'provider': 'Proveedor', 'name': 'nombre-modelo', 'description': 'Descripción del modelo'},
           ]
       )
   ```

3. Si es necesario, añadir soporte en `modelTools.py`:
   ```python
   def getLLM(agent):
       # Añadir soporte para el nuevo proveedor
       if agent.model.provider == "NuevoProveedor":
           return NuevoProveedorChat(model=agent.model.name)
   ```

### Procesamiento de Nuevos Tipos de Documentos

Para añadir soporte para nuevos tipos de documentos:

1. Añadir el loader correspondiente en `pgVectorTools.py`:
   ```python
   def index_resource(self, resource):
       # Seleccionar loader según tipo de archivo
       if resource.uri.endswith('.pdf'):
           loader = PyPDFLoader(...)
       elif resource.uri.endswith('.docx'):
           loader = DocxLoader(...)  # Nuevo tipo
       # ...
   ```

2. Actualizar la validación de formularios en las vistas correspondientes.

## Diagnóstico y Solución de Problemas

### Logs y Depuración

Para habilitar logs detallados en Flask:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Consultas y Vectores

Para depurar problemas de búsqueda vectorial:

```python
# En PGVectorTools:
def search_similar_resources(self, repository_id, embed, RESULTS=5):
    # Añadir logs
    print("Embedding query:", embed[:5], "...")
    results = vector_store.similarity_search_by_vector(...)
    print("Found results:", len(results))
    for i, res in enumerate(results):
        print(f"Result {i}:", res.page_content[:50], "...")
    return results
```

### Errores Comunes

| Error | Posible Causa | Solución |
|-------|---------------|----------|
| `OperationalError: FATAL: password authentication failed for user` | Credenciales de BD incorrectas | Verificar URI de conexión |
| `ModuleNotFoundError: No module named 'langchain_openai'` | Dependencias faltantes | Instalar requirements.txt |
| `RuntimeError: Extension vector not found` | pgvector no instalado en PostgreSQL | Instalar extensión |
| `AuthenticationError: API key not found` | Claves de API no configuradas | Configurar variables de entorno |

## Rendimiento y Optimización

### Tamaño de Chunks para RAG

El sistema actualmente utiliza un tamaño de chunk de 10 caracteres (muy pequeño, probablemente para pruebas):

```python
text_splitter = CharacterTextSplitter(chunk_size=10, chunk_overlap=0)
```

Para producción, se recomienda:
```python
text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
```

### Caché de Embeddings

Para mejorar el rendimiento, se podría implementar caché de embeddings:

```python
from langchain_core.cache import InMemoryCache
langchain.llm_cache = InMemoryCache()
```

## Estándares y Convenciones

### Manejo de Errores

Patrón recomendado para manejar errores en la API:

```python
@api_blueprint.route('/api', methods=['POST'])
def api():
    try:
        in_data = request.get_json()
        # Validar input
        if 'question' not in in_data or 'agent_id' not in in_data:
            return jsonify({"error": "Missing required fields"}), 400
            
        # Procesar
        result = process_request(in_data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

### Documentación de API

Ejemplo de documentación Swagger/OpenAPI (no implementada, pero recomendada):

```python
# app/__init__.py
from flask_restx import Api, Resource, fields

api = Api(app, version='1.0', title='IA Core Tools API',
          description='API para IA Core Tools')

question_model = api.model('Question', {
    'question': fields.String(required=True, description='Pregunta del usuario'),
    'agent_id': fields.Integer(required=True, description='ID del agente')
})

@api.route('/api')
class AgentApi(Resource):
    @api.expect(question_model)
    def post(self):
        """Envía una pregunta a un agente"""
        # Implementación
```

## Recursos Adicionales

### Herramientas de Desarrollo

- **GitHub**: Repositorio de código y gestión de issues
- **Confluence**: Documentación técnica de frontend
- **Google Drive**: Compartición de maquetas HTML

### Bibliotecas Relacionadas

- [Jinja2](https://jinja.palletsprojects.com/) - Motor de plantillas
- [pgvector](https://github.com/pgvector/pgvector) - Extensión PostgreSQL para vectores
- [langchain](https://github.com/langchain-ai/langchain) - Framework para aplicaciones LLM

### Lecturas Recomendadas

- [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401) - Paper sobre RAG
- [Building RAG-based LLM Applications for Production](https://www.pinecone.io/learn/series/langchain/langchain-rag/)
- [Full Stack Deep Learning - LLM Bootcamp](https://fullstackdeeplearning.com/llm-bootcamp/)
