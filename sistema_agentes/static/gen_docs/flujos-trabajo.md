# Flujos de Trabajo

Este documento describe los principales flujos de trabajo en el proyecto IA Core Tools, tanto desde la perspectiva de desarrollo como de uso de la aplicación.

## Flujo de Desarrollo Frontend

El desarrollo del frontend para IA Core Tools sigue un flujo estructurado que va desde el diseño hasta la implementación:

### 1. Diseño en Figma

Los diseñadores web utilizan Figma para crear:
- Maquetas de interfaz de usuario
- Especificaciones de componentes
- Guías de estilo y sistemas de diseño

### 2. Exportación como Maquetas HTML

- Los diseñadores exportan los diseños como maquetas HTML estáticas
- Estas maquetas incluyen CSS y JavaScript básico para la interactividad
- Las maquetas se comparten a través de Google Drive con los desarrolladores

### 3. Integración en el Framework Flask

Los desarrolladores:
- Convierten las maquetas HTML en plantillas Jinja2
- Implementan la lógica de backend necesaria
- Integran con las rutas y controladores de Flask
- Conectan con la base de datos y APIs

### 4. Revisión y Ajustes

- Los diseñadores revisan la implementación
- Se realizan ajustes para asegurar la fidelidad al diseño original
- Se solucionan problemas de responsividad o usabilidad

### 5. Documentación en Confluence

- La documentación del frontend se mantiene en Confluence
- Incluye patrones de UI, componentes reutilizables y guías de estilo

## Flujo de Gestión de Problemas

### 1. Identificación del Problema

Los problemas pueden ser identificados por:
- Miembros del equipo durante el desarrollo
- Pruebas internas
- Retroalimentación de usuarios
- Revisión de código

### 2. Creación de Issues en GitLab

Para cada problema identificado:
- Se crea un issue en GitLab
- Se asigna una etiqueta apropiada (bug, enhancement, feature)
- Se proporciona una descripción detallada
- Se asigna una prioridad
- Se asigna a un responsable (si corresponde)

### 3. Priorización

Durante las reuniones semanales:
- Aritz Galdos y Mikel Lonbide revisan los issues pendientes
- Se priorizan según criterios de importancia y urgencia
- Se asignan a miembros del equipo

### 4. Implementación de Soluciones

El desarrollador asignado:
- Crea una rama específica para el issue
- Implementa la solución
- Realiza pruebas locales
- Crea un Pull Request referenciando el issue

### 5. Revisión y Fusión

- Otro miembro del equipo revisa el PR
- Se solicitan cambios si es necesario
- Una vez aprobado, se fusiona a la rama principal
- El issue se cierra automáticamente al fusionar

## Flujo de Uso Principal de la Aplicación

La aplicación IA Core Tools permite a los usuarios crear y gestionar agentes de IA con capacidades RAG. A continuación se detallan los principales flujos de uso:

### 1. Creación y Configuración de Aplicaciones

```
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│  Iniciar      │     │ Formulario de │     │ Página de     │
│  sesión en    │────►│ creación de   │────►│ dashboard de  │
│  la plataforma│     │ aplicación    │     │ la aplicación │
└───────────────┘     └───────────────┘     └───────────────┘
```

Proceso:
1. El usuario inicia sesión en IA Core Tools
2. Navega a la página principal que muestra aplicaciones existentes
3. Selecciona "Crear nueva app" y completa el formulario con el nombre
4. El sistema crea la aplicación y redirige al dashboard

### 2. Gestión de Repositorios

```
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│  Dashboard de │     │ Formulario de │     │ Página de     │
│  aplicación   │────►│ creación de   │────►│ repositorio   │
│               │     │ repositorio   │     │               │
└───────────────┘     └───────────────┘     └───────────────┘
                                             │
                                             ▼
                                      ┌───────────────┐
                                      │ Carga de      │
                                      │ recursos      │
                                      │ (documentos)  │
                                      └───────────────┘
```

Proceso:
1. Desde el dashboard de la aplicación, el usuario navega a "Repositorios"
2. Crea un nuevo repositorio completando el formulario
3. En la página del repositorio, carga documentos mediante el formulario de recursos
4. El sistema procesa automáticamente los documentos cargados:
   - Extrae texto de los PDFs
   - Divide el texto en chunks
   - Genera embeddings vectoriales
   - Almacena en la base de datos pgvector

### 3. Configuración de Agentes

```
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│  Dashboard de │     │ Formulario de │     │ Página de     │
│  aplicación   │────►│ creación de   │────►│ configuración │
│               │     │ agente        │     │ del agente    │
└───────────────┘     └───────────────┘     └───────────────┘
                                             │
                                             ▼
                                      ┌───────────────┐
                                      │ Selección de  │
                                      │ repositorio   │
                                      │ y modelo      │
                                      └───────────────┘
```

Proceso:
1. Desde el dashboard de la aplicación, el usuario navega a "Agentes"
2. Crea un nuevo agente proporcionando un nombre y descripción
3. Configura el agente con:
   - Sistema prompt
   - Plantilla de prompt
   - Modelo de IA (OpenAI GPT-4o, Anthropic Claude, etc.)
   - Repositorio de conocimiento (opcional, para RAG)
   - Activación de memoria conversacional (opcional)
4. Guarda la configuración

### 4. Interacción con Agentes (Playground)

```
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│  Lista de     │     │ Playground    │     │ Envío de      │
│  agentes      │────►│ del agente    │────►│ mensaje       │
│               │     │               │     │               │
└───────────────┘     └───────────────┘     └───────┬───────┘
                                                    │
                       ┌───────────────┐            │
                       │ Visualización │            │
                       │ de respuesta  │◄───────────┘
                       │               │
                       └───────┬───────┘
                               │
                               ▼
                       ┌───────────────┐
                       │ Continuación  │
                       │ de la         │
                       │ conversación  │
                       └───────────────┘
```

Proceso:
1. El usuario selecciona un agente de la lista y accede a su playground
2. Visualiza el sistema prompt y la plantilla de prompt configurados
3. Envía un mensaje al agente mediante el formulario
4. El sistema:
   - Si el agente usa RAG: busca información relevante en el repositorio
   - Si tiene memoria conversacional: considera el contexto previo
   - Invoca al modelo de IA con el prompt formateado
   - Muestra la respuesta generada
5. El usuario puede continuar la conversación con mensajes adicionales

## Flujo de Proceso RAG

El siguiente diagrama muestra el flujo interno del proceso RAG cuando un usuario interactúa con un agente configurado con repositorio:

```
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│  Usuario envía│     │ Sistema crea  │     │ Búsqueda de   │
│  pregunta al  │────►│ embedding de  │────►│ documentos    │
│  agente RAG   │     │ la pregunta   │     │ similares     │
└───────────────┘     └───────────────┘     └───────┬───────┘
                                                    │
                       ┌───────────────┐            │
                       │ Respuesta     │            │
                       │ enviada al    │◄───────────┘
                       │ usuario       │
                       └───────────────┘
                               ▲
                               │
                       ┌───────────────┐
                       │ Modelo LLM    │
                       │ genera        │
                       │ respuesta     │
                       └───────────────┘
                               ▲
                               │
                       ┌───────────────┐
                       │ Creación de   │
                       │ prompt con    │
                       │ contexto      │
                       └───────────────┘
```

Proceso técnico:
1. El usuario envía una pregunta al agente en el playground
2. El sistema (a través de `modelTools.py`):
   - Convierte la pregunta en un vector embedding usando OpenAIEmbeddings
   - Busca documentos similares en la base de datos pgvector
   - Selecciona los fragmentos más relevantes
   - Crea un prompt que incluye estos fragmentos como contexto
   - Envía el prompt al modelo de lenguaje (OpenAI o Anthropic)
   - Recibe la respuesta generada y la muestra al usuario

## Flujo de Despliegue

El proyecto soporta dos métodos principales de despliegue:

### Despliegue Directo con Flask

```
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│  Código en    │     │ Configuración │     │ Ejecución     │
│  repositorio  │────►│ de variables  │────►│ de servidor   │
│  Git          │     │ de entorno    │     │ Flask         │
└───────────────┘     └───────────────┘     └───────────────┘
```

Proceso:
1. Clonar el repositorio en el servidor de despliegue
2. Configurar las variables de entorno necesarias
3. Instalar dependencias con pip
4. Ejecutar las migraciones de Alembic
5. Iniciar el servidor Flask

### Despliegue con Docker

```
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│  Código en    │     │ Construcción  │     │ Ejecución de  │
│  repositorio  │────►│ de imágenes   │────►│ contenedores  │
│  Git          │     │ Docker        │     │ con Docker    │
└───────────────┘     └───────────────┘     │ Compose       │
                                            └───────────────┘
```

Proceso:
1. Clonar el repositorio en el servidor de despliegue
2. Configurar las variables de entorno en `docker-compose.yaml`
3. Construir las imágenes Docker
4. Iniciar los contenedores con Docker Compose
