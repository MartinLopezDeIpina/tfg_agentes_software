# Sistema de Gestión de Tareas

Este documento describe el sistema utilizado para gestionar las tareas y el flujo de trabajo en el proyecto IA Core Tools.

## Gestión de Issues en GitHub

El proyecto utiliza el sistema de issues de GitHub como principal herramienta para el seguimiento y la gestión de tareas.

### Tipos de Issues

1. **Nuevas Funcionalidades**: Implementación de nuevas capacidades para el sistema
2. **Correcciones de Errores**: Solución de problemas identificados
3. **Mejoras**: Optimizaciones o refinamientos de funcionalidades existentes
4. **Documentación**: Creación o actualización de documentación
5. **Tareas Técnicas**: Configuración, refactorización, actualización de dependencias, etc.

### Estructura de un Issue

Cada issue debe contener la siguiente información:

- **Título**: Breve descripción de la tarea (menos de 50 caracteres)
- **Descripción**: Explicación detallada del problema o funcionalidad
- **Criterios de Aceptación**: Condiciones que deben cumplirse para considerar completada la tarea
- **Etiquetas**: Categorización del issue (bug, feature, documentation, etc.)
- **Asignado**: Persona responsable de completar la tarea
- **Milestone** (opcional): Agrupación de issues para una entrega específica
- **Estimación** (opcional): Complejidad o tiempo estimado para completar la tarea

### Estado de los Issues

Los issues pueden estar en uno de los siguientes estados:

1. **Open/Backlog**: Tareas pendientes de asignación o inicio
2. **In Progress**: Tareas actualmente en desarrollo
3. **Review**: Tareas completadas, pendientes de revisión
4. **Done**: Tareas completadas y verificadas

## Proceso de Gestión de Tareas

### Creación y Priorización

1. Cualquier miembro del equipo puede crear issues para documentar tareas o problemas
2. Durante las reuniones semanales, Aritz Galdos y Mikel Lonbide revisan los issues abiertos y deciden las prioridades
3. Se asignan los issues priorizados a los miembros del equipo según disponibilidad y especialización

### Desarrollo

1. El desarrollador asignado mueve el issue al estado "In Progress"
2. Crea una rama específica para la tarea siguiendo la convención de nomenclatura:
   ```
   tipo/descripcion-breve
   ```
   Por ejemplo: `feature/upload-resources` o `fix/session-management`
3. Desarrolla la solución implementando los cambios necesarios
4. Realiza commits frecuentes con mensajes descriptivos

### Revisión y Fusión

1. Una vez completada la tarea, el desarrollador crea un Pull Request (PR)
2. El PR debe referenciar el issue correspondiente (por ejemplo, "Fixes #123")
3. El PR es revisado por al menos un miembro del equipo
4. Si se solicitan cambios, el desarrollador los implementa y actualiza el PR
5. Una vez aprobado, el PR es fusionado a la rama principal (develop)
6. El issue se cierra automáticamente si el PR contiene las palabras clave adecuadas

## Seguimiento del Progreso

### Tablero de Proyecto

El proyecto utiliza el tablero de proyectos de GitHub para visualizar el estado de las tareas en curso:

- **To Do**: Issues pendientes priorizados
- **In Progress**: Issues actualmente en desarrollo
- **Review**: Issues pendientes de revisión
- **Done**: Issues completados recientemente

### Reuniones de Seguimiento

Durante las reuniones semanales, el equipo revisa:

1. Issues completados desde la última reunión
2. Issues en progreso y posibles bloqueos
3. Issues planificados para la próxima semana

## Convenciones de Branches y Commits

### Branches

- **main**: Código estable, listo para producción
- **develop**: Rama de integración para desarrollo
- **feature/[descripción]**: Nuevas funcionalidades
- **fix/[descripción]**: Correcciones de errores
- **refactor/[descripción]**: Refactorizaciones
- **docs/[descripción]**: Cambios en documentación

### Mensajes de Commit

Los mensajes de commit deben seguir esta estructura:

```
tipo: descripción breve

Descripción detallada si es necesaria.
Referencias a issues (#numero).
```

Donde `tipo` puede ser:
- **feat**: Nueva funcionalidad
- **fix**: Corrección de errores
- **docs**: Cambios en documentación
- **style**: Cambios en el formato del código (no funcionales)
- **refactor**: Refactorización de código existente
- **test**: Adición o modificación de pruebas
- **chore**: Cambios en el proceso de construcción, herramientas, etc.

## Gestión de Versiones

El proyecto sigue un esquema de versionado semántico (SemVer):

- **Mayor (X.0.0)**: Cambios incompatibles con versiones anteriores
- **Menor (0.X.0)**: Nuevas funcionalidades compatibles con versiones anteriores
- **Parche (0.0.X)**: Correcciones de errores compatibles con versiones anteriores

## Flujo de Trabajo de Integración Continua

1. Los cambios son integrados primero en la rama `develop`
2. Se realizan pruebas automáticas o manuales en esta rama
3. Periódicamente, cuando `develop` está estable, se fusiona con `main`
4. Se genera una nueva versión a partir de `main`

## Herramientas Complementarias

Además del sistema de issues de GitHub, el equipo utiliza:

- **Chats de Gmail y Microsoft Teams**: Para discusiones rápidas sobre tareas
- **Reuniones presenciales en Zuatzu**: Para planificación y resolución de problemas complejos
- **Confluence**: Para documentación técnica detallada, especialmente relacionada con el frontend
