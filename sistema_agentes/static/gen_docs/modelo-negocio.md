# Modelo de Dominio

Este documento describe el modelo de dominio de IA Core Tools, detallando las entidades principales, sus relaciones y el flujo de datos dentro del sistema.

## Visión General del Dominio

IA Core Tools es una plataforma diseñada para permitir la creación, configuración y gestión de agentes de IA basados en técnicas de Retrieval-Augmented Generation (RAG). El dominio se centra en la integración de grandes modelos de lenguaje (LLMs) con bases de conocimiento personalizadas para crear asistentes inteligentes que puedan responder preguntas basándose en datos específicos.

## Entidades Principales

### App

Una `App` representa el contenedor principal de la aplicación que agrupa diversos componentes como agentes y repositorios.

**Atributos:**
- `app_id`: Identificador único de la aplicación
- `name`: Nombre descriptivo de la aplicación

**Relaciones:**
- Una App puede tener múltiples Repositories (relación uno a muchos)
- Una App puede tener múltiples Agents (relación uno a muchos)

**Responsabilidades:**
- Servir como punto de entrada a la aplicación
- Organizar agentes y repositorios relacionados temáticamente
- Permitir gestionar el acceso y los permisos a nivel de aplicación

### Repository

Un `Repository` es una colección de recursos o documentos que sirven como base de conocimiento para los agentes de IA.

**Atributos:**
- `repository_id`: Identificador único del repositorio
- `name`: Nombre descriptivo del repositorio
- `type`: Tipo de repositorio (categorización)
- `status`: Estado actual del repositorio

**Relaciones:**
- Un Repository pertenece a una App (relación muchos a uno)
- Un Repository puede contener múltiples Resources (relación uno a muchos)
- Un Repository puede estar asociado a múltiples Agents (relación uno a muchos)

**Responsabilidades:**
- Almacenar y organizar recursos relacionados
- Servir como base de conocimiento para los agentes
- Permitir la búsqueda vectorial de contenido relevante

### Resource

Un `Resource` representa un documento o archivo individual (típicamente PDF) que contiene información que puede ser utilizada por los agentes de IA.

**Atributos:**
- `resource_id`: Identificador único del recurso
- `name`: Nombre descriptivo del recurso
- `uri`: Ubicación del archivo en el sistema
- `type`: Tipo de recurso (PDF, etc.)
- `status`: Estado actual del recurso

**Relaciones:**
- Un Resource pertenece a un Repository (relación muchos a uno)

**Responsabilidades:**
- Almacenar el contenido informativo
- Servir como fuente de datos para la vectorización
- Proporcionar contexto para las respuestas de los agentes

### Agent

Un `Agent` es una configuración específica de un asistente de IA que puede interactuar con usuarios utilizando un modelo de lenguaje y, opcionalmente, un repositorio de conocimiento.

**Atributos:**
- `agent_id`: Identificador único del agente
- `name`: Nombre descriptivo del agente
- `description`: Descripción del propósito y capacidades del agente
- `system_prompt`: Instrucciones del sistema que definen el comportamiento del agente
- `prompt_template`: Plantilla utilizada para formatear las consultas al modelo
- `type`: Categorización del agente
- `status`: Estado actual del agente
- `has_memory`: Indicador de si el agente mantiene memoria conversacional

**Relaciones:**
- Un Agent puede pertenecer a una App (relación muchos a uno)
- Un Agent puede estar asociado a un Repository (relación muchos a uno)
- Un Agent puede utilizar un Model específico (relación muchos a uno)

**Responsabilidades:**
- Proporcionar una interfaz para la interacción con el usuario
- Procesar las consultas utilizando un modelo de lenguaje
- Incorporar conocimiento relevante de un repositorio (RAG)
- Mantener el contexto conversacional cuando sea necesario

### Model

Un `Model` representa un modelo de lenguaje específico que puede ser utilizado por los agentes para generar respuestas.

**Atributos:**
- `model_id`: Identificador único del modelo
- `provider`: Proveedor del modelo (OpenAI, Anthropic, etc.)
- `name`: Nombre del modelo específico (gpt-4o, claude-3.5-sonnet, etc.)
- `description`: Descripción de las capacidades y características del modelo

**Relaciones:**
- Un Model puede ser utilizado por múltiples Agents (relación uno a muchos)

**Responsabilidades:**
- Definir las características y capacidades del modelo de lenguaje
- Permitir la selección del modelo apropiado según las necesidades del agente

### User

Un `User` representa un usuario del sistema con acceso a aplicaciones y sus componentes.

**Atributos:**
- `user_id`: Identificador único del usuario
- `email`: Dirección de correo electrónico del usuario
- `name`: Nombre del usuario

**Relaciones:**
- No definidas explícitamente en el código actual, pero potencialmente podría tener relaciones con Apps, Agents, etc.

**Responsabilidades:**
- Autenticación y autorización en el sistema
- Gestión de permisos y acceso a recursos

## Relaciones y Cardinalidad

```
App (1) --- (*) Repository
App (1) --- (*) Agent
Repository (1) --- (*) Resource
Repository (1) --- (*) Agent
Model (1) --- (*) Agent
```

## Diagrama de Modelo de Dominio

```
+--------+      +-------------+      +---------+
|        |      |             |      |         |
|  App   |<-----| Repository  |<-----| Resource|
|        |      |             |      |         |
+--------+      +-------------+      +---------+
    ^                 ^
    |                 |
    |                 |
+--------+      +-------------+
|        |      |             |
|  Agent |----->|   Model     |
|        |      |             |
+--------+      +-------------+
```

## Flujos Principales del Dominio

### Flujo de Creación y Configuración

1. Un usuario crea una `App` como contenedor principal
2. Dentro de la App, el usuario crea uno o más `Repository` para organizar el conocimiento
3. El usuario carga `Resource` (documentos) en cada Repository
4. El sistema procesa los Resources:
   - Extrae texto de documentos PDF
   - Divide el texto en fragmentos (chunks)
   - Genera embeddings vectoriales para cada fragmento
   - Almacena los vectores en la base de datos pgvector
5. El usuario crea `Agent` dentro de la App:
   - Configura el system prompt y prompt template
   - Selecciona un `Model` (OpenAI, Anthropic)
   - Opcionalmente asocia el Agent con un Repository para RAG
   - Opcionalmente activa la memoria conversacional

### Flujo de Consulta (RAG)

1. Un usuario envía una consulta a un `Agent` configurado
2. El sistema:
   - Convierte la consulta en un vector embedding
   - Busca fragmentos de texto similares en el `Repository` asociado
   - Selecciona los fragmentos más relevantes
   - Construye un prompt que incluye estos fragmentos como contexto
   - Envía el prompt al `Model` seleccionado (OpenAI, Anthropic)
   - Recibe la respuesta generada y la muestra al usuario
3. Si el `Agent` tiene memoria conversacional activada:
   - El sistema mantiene el historial de la conversación
   - Incluye mensajes anteriores al construir nuevos prompts

## Invariantes y Reglas de Negocio

1. Cada `Agent` debe tener un system prompt y prompt template definidos
2. Para funcionalidad RAG, un `Agent` debe estar asociado a un `Repository`
3. Los `Resource` deben estar en formatos compatibles (actualmente PDF)
4. Un `Agent` con memoria conversacional mantiene historial de mensajes para contextualizar respuestas
5. Cada `App` funciona como un contenedor aislado de agentes y repositorios relacionados

## Ejemplos de Configuración

### Ejemplo 1: Agente Simple sin RAG

```
App: "Asistente Técnico"
  Agent: "Ayudante General"
    System Prompt: "Eres un asistente técnico útil y preciso..."
    Prompt Template: "Por favor, responde a esta pregunta: {question}"
    Model: "gpt-4o"
    Has Memory: false
    Repository: null
```

### Ejemplo 2: Agente RAG con Memoria

```
App: "Soporte Producto X"
  Repository: "Documentación Técnica"
    Resource: "manual_usuario.pdf"
    Resource: "especificaciones_tecnicas.pdf"
  Agent: "Especialista Producto X"
    System Prompt: "Eres un experto en el Producto X..."
    Prompt Template: "Responde basándote en la documentación: {question}"
    Model: "claude-3.5-sonnet"
    Has Memory: true
    Repository: "Documentación Técnica"
```

## Evolución del Modelo de Dominio

El modelo de dominio actual refleja la versión implementada, pero se prevén posibles extensiones:

1. Implementación completa de `User` con gestión de permisos
2. Adición de `Crawler` para indexación automática de contenido (mencionado en la interfaz)
3. Soporte para tipos adicionales de recursos (actualmente limitado a PDF)
4. Gestión de `API Keys` para integración con sistemas externos

## Consideraciones Técnicas

1. La vectorización de documentos utiliza OpenAIEmbeddings
2. Los vectores se almacenan en PostgreSQL con la extensión pgvector
3. La búsqueda de similitud se realiza mediante distancia coseno entre vectores
4. La memoria conversacional se implementa mediante ConversationBufferMemory de Langchain
5. El procesamiento de documentos utiliza PyPDFLoader y CharacterTextSplitter

Este modelo de dominio refleja la estructura actual del sistema IA Core Tools y proporciona una base para entender las entidades, relaciones y flujos principales de la aplicación.
