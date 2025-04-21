# Guía de Contribución

Esta guía proporciona instrucciones detalladas sobre cómo contribuir efectivamente al proyecto IA Core Tools. Está diseñada para asegurar que todas las contribuciones mantengan la calidad y coherencia del código.

## Requisitos Previos

Antes de comenzar a contribuir, asegúrate de tener instalado y configurado:

1. Python 3.11 o superior
2. PostgreSQL con extensión pgvector
3. Docker y Docker Compose (recomendado para desarrollo)
4. Git

## Configuración del Entorno de Desarrollo

### Clonar el Repositorio

```bash
git clone [URL_DEL_REPOSITORIO]
cd ia-core-tools
```

### Configurar el Entorno Virtual

```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r app/requirements.txt
```

### Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto con las siguientes variables:

```
SQLALCHEMY_DATABASE_URI=postgresql://iacore:iacore@postgres:5432/iacore
OPENAI_API_KEY=tu_api_key
ANTHROPIC_API_KEY=tu_api_key
REPO_BASE_FOLDER=ruta_para_almacenar_documentos
```

### Iniciar la Base de Datos

```bash
alembic upgrade head
```

### Ejecutar la Aplicación

```bash
cd app && flask run
```

o con Docker:

```bash
docker-compose up -d
```

## Flujo de Trabajo para Contribuciones

### 1. Crear o Seleccionar un Issue

Antes de comenzar a trabajar en una nueva funcionalidad o corrección, asegúrate de que existe un issue correspondiente en GitHub. Si no existe, créalo detallando:

- Descripción clara del problema o funcionalidad
- Comportamiento esperado
- Criterios de aceptación

### 2. Crear una Rama

Crea una rama específica para tu contribución siguiendo la convención de nomenclatura:

```bash
git checkout -b tipo/descripcion-breve
```

Donde `tipo` puede ser:
- `feature` para nuevas funcionalidades
- `fix` para correcciones de errores
- `refactor` para refactorizaciones de código
- `docs` para cambios en la documentación

### 3. Implementar Cambios

Desarrolla la funcionalidad o corrección siguiendo las prácticas y estándares de código del proyecto. Asegúrate de:

- Seguir la estructura del proyecto existente
- Mantener la coherencia en el estilo de código
- Documentar el código nuevo adecuadamente

### 4. Pruebas

Asegúrate de que tu código funciona correctamente. Prueba manualmente las funcionalidades implementadas y, si es posible, añade pruebas automatizadas.

### 5. Commit de Cambios

Realiza commits con mensajes claros y descriptivos:

```bash
git add .
git commit -m "tipo: descripción concisa del cambio"
```

### 6. Actualizar tu Rama

Antes de enviar tu Pull Request, actualiza tu rama con los últimos cambios de la rama principal:

```bash
git checkout main
git pull
git checkout tu-rama
git rebase main
```

Resuelve cualquier conflicto que pueda surgir.

### 7. Enviar Pull Request

Crea un Pull Request en GitHub con:

- Título claro que referencia el issue (ej. "Fix #123: Corrección en el manejo de sesiones")
- Descripción detallada de los cambios realizados
- Menciones a cualquier dependencia o consideración especial

### 8. Revisión de Código

Tu código será revisado por otros miembros del equipo. Responde a cualquier comentario o solicitud de cambios de manera oportuna.

### 9. Fusión

Una vez aprobado, tu Pull Request será fusionado con la rama principal por el mantenedor del proyecto.

## Estructura del Proyecto

Para contribuir efectivamente, es importante entender la estructura del proyecto:

```
ia-core-tools/
├── alembic/                 # Migraciones de base de datos
├── app/
│   ├── api/                 # Endpoints de API
│   ├── db/                  # Configuración de base de datos
│   ├── model/               # Modelos SQLAlchemy
│   ├── static/              # Archivos estáticos
│   ├── templates/           # Plantillas HTML
│   ├── tools/               # Utilidades para modelos y vectores
│   ├── views/               # Rutas de Flask
│   ├── app.py               # Aplicación principal
│   └── extensions.py        # Extensiones de Flask
├── docs/                    # Documentación
├── notebooks/               # Cuadernos Jupyter para experimentación
└── docker-compose.yaml      # Configuración de Docker
```

## Convenciones de Código

### Python

- Sigue PEP 8 para el estilo de código
- Usa nombres descriptivos para variables y funciones
- Comenta el código cuando sea necesario para explicar la lógica compleja
- Usa docstrings para documentar funciones, clases y módulos

### HTML/Templates

- Utiliza la estructura de plantillas de Jinja2 consistentemente
- Mantén una indentación clara y consistente
- Separa la lógica de presentación de la lógica de negocio

### SQL/Alembic

- Para cambios en el esquema de la base de datos, usa migraciones de Alembic:
  ```bash
  alembic revision --autogenerate -m "Descripción del cambio"
  ```

## Licencia y Derechos de Autor

Al contribuir a este proyecto, aceptas que tus contribuciones estarán licenciadas bajo la LKS Inner Source License (LKSISL), como se indica en el archivo LICENSE.md.

## Preguntas y Soporte

Si tienes preguntas sobre cómo contribuir o necesitas ayuda con cualquier aspecto del proceso, no dudes en:

- Contactar a Aritz Galdos o Mikel Lonbide directamente
- Crear un issue con la etiqueta "pregunta" o "ayuda"
- Preguntar en los canales de comunicación del equipo
