# Arquitectura de Software

Este documento describe la arquitectura del sistema IA Core Tools en varios niveles de abstracción, desde la visión general hasta los componentes detallados.

## Nivel 1: Visión General del Sistema

IA Core Tools es una plataforma web que permite crear, configurar y gestionar agentes de IA basados en técnicas de Retrieval-Augmented Generation (RAG). El sistema facilita la integración de grandes modelos de lenguaje (LLMs) con bases de conocimiento personalizadas para crear asistentes inteligentes adaptados a diferentes necesidades empresariales.

### Usuarios y Contexto

- **Usuarios Primarios**: Equipos técnicos internos de LKS Next
- **Casos de Uso Principal**: Desarrollo de soluciones de IA para clientes como Orona
- **Sistemas Externos**: Integraciones con APIs de OpenAI y Anthropic para modelos de lenguaje

### Diagrama de Contexto

```
┌───────────────────────────────────────────────────────────┐
│                                                           │
│                      Usuarios LKS Next                    │
│                                                           │
└───────────────┬───────────────────────────┬───────────────┘
                │                           │
                ▼                           ▼
┌───────────────────────────┐   ┌───────────────────────────┐
│                           │   │                           │
│     IA Core Tools         │◄──┤   Documentos/Datos        │
│     (Plataforma Web)      │   │   (Repositorios)          │
│                           │   │                           │
└───────────┬───────────────┘   └───────────────────────────┘
            │
            ▼
┌───────────────────────────┐   ┌───────────────────────────┐
│                           │   │                           │
│    API OpenAI             │   │    API Anthropic          │
│    (GPT-4o, etc.)         │   │    (Claude, etc.)         │
│                           │   │                           │
└───────────────────────────┘   └───────────────────────────┘
```

## Nivel 2: Contenedores (Componentes Principales)

El sistema se divide en varios componentes principales que interactúan entre sí:

### Componentes Principales

1. **Aplicación Web Flask**: Interfaz de usuario y lógica de negocio
2. **Base de Datos PostgreSQL**: Almacenamiento persistente de datos con extensión pgvector para búsqueda vectorial
3. **Servicio de Vectorización**: Convierte documentos en embeddings vectoriales
4. **Administrador de Modelos**: Gestiona la interacción con LLMs externos
5. **Sistema de Almacenamiento de Archivos**: Maneja documentos y recursos

### Interacciones entre Componentes

```
┌────────────────────────────────────────────────────────────────────┐
│                           IA Core Tools                             │
│                                                                     │
│  ┌───────────────────┐           ┌───────────────────────────────┐  │
│  │                   │           │                               │  │
│  │  Aplicación Web   │◄─────────►│  Administrador de Modelos     │──┼──┐
│  │  Flask            │           │  (ModelTools)                 │  │  │
│  │                   │           │                               │  │  │
│  └─────────┬─────────┘           └───────────────────────────────┘  │  │
│            │                                                         │  │
│            ▼                                                         │  │
│  ┌─────────────────────┐       ┌────────────────────────────────┐   │  │
│  │                     │       │                                │   │  │
│  │  Base de Datos      │◄─────►│  Servicio de Vectorización     │   │  │
│  │  PostgreSQL +       │       │  (PGVectorTools)               │   │  │
│  │  pgvector           │       │                                │   │  │
│  │                     │       └────────────────────────────────┘   │  │
│  └─────────────────────┘                                            │  │
│            ▲                                                         │  │
│            │                                                         │  │
│            ▼                                                         │  │
│  ┌───────────────────────┐                                           │  │
│  │                       │                                           │  │
│  │  Sistema de           │                                           │  │
│  │  Almacenamiento       │                                           │  │
│  │  de Archivos          │                                           │  │
│  │                       │                                           │  │
│  └───────────────────────┘                                           │  │
│                                                                      │  │
└──────────────────────────────────────────────────────────────────────┘  │
                                                                           │
                                                                           ▼
┌─────────────────────────────────────┐  ┌─────────────────────────────────────┐
│                                     │  │                                     │
│  API OpenAI                         │  │  API Anthropic                      │
│  (GPT-4o, GPT-4o-mini)              │  │  (Claude-3.5-sonnet, Claude-3-opus) │
│                                     │  │                                     │
└─────────────────────────────────────┘  └─────────────────────────────────────┘
```

## Nivel 3: Componentes

Cada contenedor principal se descompone en componentes más específicos:

### Aplicación Web Flask

- **Blueprints**:
  - `agents_blueprint`: Gestión de agentes de IA
  - `repositories_blueprint`: Gestión de repositorios de conocimiento
  - `resources_blueprint`: Gestión de recursos dentro de repositorios
  - `api_blueprint`: Endpoints de API para interactuar con agentes

- **Modelo de Datos**:
  - `App`: Aplicación contenedora de agentes y repositorios
  - `Agent`: Configura un asistente de IA específico
  - `Repository`: Colección de recursos/documentos
  - `Resource`: Documento individual (PDF, etc.)
  - `Model`: Configuración de modelos de LLM disponibles

### Servicio de Vectorización

- **PGVectorTools**: Gestiona la indexación y búsqueda de contenido
  - Creación de tablas vectoriales
  - Indexación de recursos
  - Búsqueda por similitud
  - Creación de retrievers para RAG

### Administrador de Modelos

- **ModelTools**: Orquesta interacciones con modelos de lenguaje
  - Invocación de modelos
  - Implementación de RAG
  - Gestión de memoria conversacional
  - Selección de modelos apropiados

## Nivel 4: Código y Flujos de Datos

A este nivel, exploramos componentes específicos con mayor detalle:

### Ejemplo: Flujo de Procesamiento RAG

```
┌───────────────────┐     ┌─────────────────────┐     ┌────────────────────┐
│                   │     │                     │     │                    │
│  Recurso (PDF)    │────►│  PyPDFLoader        │────►│  Segmentación      │
│                   │     │                     │     │  (text_splitter)   │
│                   │     │                     │     │                    │
└───────────────────┘     └─────────────────────┘     └────────┬───────────┘
                                                               │
                                                               ▼
┌───────────────────┐     ┌─────────────────────┐     ┌────────────────────┐
│                   │     │                     │     │                    │
│  Almacenamiento   │◄────┤  Creación de        │◄────┤  Generación de     │
│  en pgvector      │     │  Embeddings         │     │  Chunks            │
│                   │     │                     │     │                    │
└───────────────────┘     └─────────────────────┘     └────────────────────┘
```

### Ejemplo: Flujo de Consulta a un Agente

```
┌────────────┐    ┌────────────────┐    ┌──────────────────┐
│            │    │                │    │                  │
│  Pregunta  │───►│  Embeddings    │───►│  Búsqueda        │
│  del Usuario│    │  de Consulta   │    │  de Similitud    │
│            │    │                │    │                  │
└────────────┘    └────────────────┘    └────────┬─────────┘
                                                 │
                                                 ▼
┌────────────┐    ┌────────────────┐    ┌──────────────────┐
│            │    │                │    │                  │
│  Respuesta │◄───┤  LLM           │◄───┤  Prompt con      │
│  Final     │    │  (OpenAI/      │    │  Contexto        │
│            │    │  Anthropic)    │    │                  │
└────────────┘    └────────────────┘    └──────────────────┘
```

### Componente: PGVectorTools

Este componente gestiona la interacción con la base de datos vectorial:

```python
class PGVectorTools:
    def __init__(self, db):
        """Initializes the PGVectorTools with a SQLAlchemy engine."""
        self.Session = db.session
        self.db = db    

    def create_pgvector_table(self, repository_id):
        """Creates a pgvector table for the given repository if it doesn't exist."""
        # Implementación...

    def index_resource(self, resource):
        """Indexes a resource by loading its content, splitting it into chunks, and adding it to the pgvector table."""
        # Cargar documento con PyPDFLoader
        # Dividir en fragmentos con CharacterTextSplitter
        # Almacenar en PGVector con OpenAIEmbeddings

    def search_similar_resources(self, repository_id, embed, RESULTS=5):
        """Searches for similar resources in the pgvector table using langchain vector store."""
        # Buscar documentos similares según embedding

    def get_pgvector_retriever(self, repository_id):
        """Returns a retriever object for the pgvector collection."""
        # Crear y devolver un objeto retriever
```

### Componente: ModelTools

Este componente gestiona la interacción con modelos de lenguaje:

```python
def invoke(agent, input):
    """Invoca un modelo de lenguaje básico sin RAG"""
    # Crear prompt con la plantilla del agente
    # Invocar el modelo LLM
    # Devolver la respuesta

def invoke_rag_with_repo(agent, input):
    """Invoca un modelo con RAG usando repositorio"""
    # Convertir input a embedding
    # Buscar recursos similares
    # Crear prompt con contexto encontrado
    # Invocar el modelo LLM
    # Devolver la respuesta

def invoke_ConversationalRetrievalChain(agent, input, session):
    """Invoca un modelo con RAG y memoria conversacional"""
    # Configurar memoria de conversación
    # Crear retriever de documentos
    # Configurar chain conversacional
    # Invocar chain y devolver respuesta
```

## Consideraciones Arquitectónicas

### Escalabilidad

- **Vertical**: La aplicación puede escalar verticalmente aumentando recursos del servidor
- **Horizontal**: Posibilidad de implementar balance de carga para múltiples instancias

### Extensibilidad

La arquitectura está diseñada para facilitar la adición de:
- Nuevos modelos de LLM
- Diferentes tipos de repositorios y formatos de documentos
- Funcionalidades adicionales mediante blueprints de Flask

### Seguridad

- Gestión de credenciales de API mediante variables de entorno
- Autenticación a nivel de sesión
- Validación de entradas en formularios y API

### Dependencias Externas

- **APIs de Modelos**: OpenAI (GPT-4o) y Anthropic (Claude)
- **Bases de Datos**: PostgreSQL con extensión pgvector
- **Procesamiento de Documentos**: PyPDF, langchain

## Decisiones Arquitectónicas

### Elección de Flask

Flask fue seleccionado por su ligereza y flexibilidad, permitiendo construir una aplicación web con bajo overhead que se integra bien con otros componentes.

### Uso de pgvector en PostgreSQL

La extensión pgvector de PostgreSQL ofrece capacidades de búsqueda vectorial eficientes, eliminando la necesidad de sistemas adicionales como Milvus o Pinecone.

### Organización en Blueprints

La estructura basada en blueprints permite una organización modular del código, facilitando el mantenimiento y la extensión.

### Langchain como Framework de RAG

Se utiliza Langchain para simplificar la implementación de técnicas RAG, proporcionando componentes reutilizables para la gestión de documentos, vectorización y encadenamiento de operaciones.
