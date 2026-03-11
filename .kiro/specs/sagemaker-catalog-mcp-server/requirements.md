# Documento de Requisitos

## Introducción

Este documento define los requisitos para el SageMaker Catalog MCP Server, un servidor MCP (Model Context Protocol) que expone la totalidad de las operaciones de la API de Amazon SageMaker Catalog como tools MCP. SageMaker Catalog utiliza Amazon DataZone como servicio subyacente, por lo que las operaciones expuestas corresponden a la API de DataZone.

Existe un MCP server de referencia (`awslabs/amazon-datazone-mcp-server`, v0.1.1) que cubre 49 de 176 operaciones (~28%) con tools escritas manualmente. Este proyecto busca reemplazarlo con un enfoque de auto-generación desde el service model de botocore, logrando cobertura del 100% de la API y permitiendo actualizaciones automáticas cuando AWS agrega nuevas operaciones (simplemente actualizando la versión de boto3).

## Glosario

- **MCP_Server**: Servidor que implementa el Model Context Protocol, exponiendo tools que un cliente MCP puede invocar.
- **Tool**: Una operación individual expuesta por el MCP_Server que un cliente puede llamar con parámetros específicos.
- **Service_Model**: Archivo JSON de botocore (`service-2.json`) que describe todas las operaciones, shapes de entrada/salida, documentación y tipos de la API de DataZone.
- **Generador**: Módulo que lee el Service_Model de botocore y produce definiciones de tools MCP automáticamente.
- **Shape**: Definición de estructura de datos en el Service_Model que describe los parámetros de entrada o salida de una operación.
- **Operación**: Una acción individual de la API de DataZone (ej: `ListDomains`, `CreateProject`).
- **Cliente_MCP**: Aplicación que se conecta al MCP_Server para invocar tools (ej: un IDE con soporte MCP).
- **Transporte_Stdio**: Mecanismo de comunicación donde el MCP_Server lee de stdin y escribe a stdout.
- **Transporte_HTTP**: Mecanismo de comunicación donde el MCP_Server expone un endpoint HTTP Streamable.
- **Server_Existente**: El MCP server de referencia `awslabs/amazon-datazone-mcp-server` (v0.1.1) que cubre 49 operaciones con tools escritas manualmente.
- **SageMaker_Catalog**: Servicio de AWS que proporciona un catálogo de datos empresarial, implementado sobre Amazon DataZone. Las APIs son idénticas.

## Requisitos

### Requisito 1: Lectura y parseo del Service Model de botocore

**Historia de Usuario:** Como desarrollador del MCP Server, quiero que el sistema lea y parsee el service model de DataZone desde botocore, para que las definiciones de tools se generen automáticamente a partir de la fuente oficial.

#### Criterios de Aceptación

1. WHEN el Generador se inicializa, THE Generador SHALL localizar y leer el archivo `service-2.json` de DataZone desde el paquete botocore instalado.
2. WHEN el Generador parsea el Service_Model, THE Generador SHALL extraer la lista completa de operaciones con sus nombres, documentación, y shapes de entrada y salida.
3. WHEN el Generador parsea un Shape de tipo estructura, THE Generador SHALL extraer todos los miembros con sus nombres, tipos, documentación, y si son requeridos u opcionales.
4. WHEN el Generador parsea un Shape de tipo lista o mapa, THE Generador SHALL resolver recursivamente los tipos internos hasta llegar a tipos primitivos o estructuras.
5. IF el archivo `service-2.json` no se encuentra en botocore, THEN THE Generador SHALL reportar un error descriptivo indicando la ruta esperada y la versión de botocore instalada.
6. THE Generador SHALL producir una representación intermedia equivalente al parsear el Service_Model y luego serializarlo de vuelta (propiedad round-trip).

### Requisito 2: Generación automática de tools MCP desde el Service Model

**Historia de Usuario:** Como desarrollador del MCP Server, quiero que cada operación de DataZone se convierta automáticamente en una tool MCP, para que el servidor tenga cobertura del 100% de la API sin escribir código manual por operación.

#### Criterios de Aceptación

1. WHEN el Generador procesa el Service_Model, THE Generador SHALL crear una definición de Tool por cada operación encontrada en el Service_Model.
2. WHEN el Generador crea una definición de Tool, THE Generador SHALL asignar un nombre derivado del nombre de la operación usando convención snake_case.
3. WHEN el Generador crea una definición de Tool, THE Generador SHALL generar una descripción a partir de la documentación de la operación en el Service_Model.
4. WHEN el Generador crea una definición de Tool, THE Generador SHALL definir el esquema de parámetros de entrada basándose en el input shape de la operación, incluyendo tipos, descripciones, y campos requeridos.
5. WHEN el Generador procesa shapes anidados, THE Generador SHALL convertir tipos de botocore a tipos JSON Schema (string, integer, boolean, array, object).
6. THE Generador SHALL generar exactamente una Tool por cada operación en el Service_Model, sin omitir ni duplicar operaciones.

### Requisito 3: Registro dinámico de tools en el MCP Server

**Historia de Usuario:** Como usuario del MCP Server, quiero que todas las tools generadas se registren automáticamente al iniciar el servidor, para que pueda invocar cualquier operación de DataZone sin configuración adicional.

#### Criterios de Aceptación

1. WHEN el MCP_Server se inicia, THE MCP_Server SHALL invocar al Generador y registrar todas las tools generadas.
2. WHEN un Cliente_MCP solicita la lista de tools disponibles, THE MCP_Server SHALL retornar todas las tools registradas con sus nombres, descripciones y esquemas de parámetros.
3. WHEN el MCP_Server registra las tools, THE MCP_Server SHALL completar el registro de las 176 operaciones en menos de 10 segundos.
4. IF el Generador falla durante la inicialización, THEN THE MCP_Server SHALL reportar el error y terminar con un código de salida distinto de cero.

### Requisito 4: Ejecución de tools contra la API de AWS

**Historia de Usuario:** Como usuario del MCP Server, quiero invocar cualquier tool y que ejecute la operación correspondiente contra la API de DataZone, para que pueda gestionar recursos de SageMaker Catalog desde un cliente MCP.

#### Criterios de Aceptación

1. WHEN un Cliente_MCP invoca una Tool con parámetros válidos, THE MCP_Server SHALL ejecutar la operación correspondiente de DataZone usando boto3 y retornar el resultado.
2. WHEN el MCP_Server ejecuta una operación, THE MCP_Server SHALL serializar la respuesta de boto3 a formato JSON legible para el Cliente_MCP.
3. WHEN un Cliente_MCP invoca una Tool con parámetros que no cumplen el esquema requerido, THE MCP_Server SHALL retornar un error de validación indicando los parámetros faltantes o inválidos.
4. IF la API de AWS retorna un error (AccessDenied, ResourceNotFound, Throttling, etc.), THEN THE MCP_Server SHALL retornar un mensaje de error estructurado con el código de error, mensaje, y operación que falló.
5. IF la conexión con AWS falla por timeout o error de red, THEN THE MCP_Server SHALL retornar un error descriptivo sin terminar el proceso del servidor.

### Requisito 5: Soporte de transporte stdio

**Historia de Usuario:** Como usuario, quiero conectar el MCP Server a mi IDE usando transporte stdio, para que pueda usarlo localmente sin configurar infraestructura de red.

#### Criterios de Aceptación

1. THE MCP_Server SHALL soportar transporte stdio como mecanismo de comunicación por defecto.
2. WHEN el MCP_Server se ejecuta con transporte stdio, THE MCP_Server SHALL leer mensajes JSON-RPC desde stdin y escribir respuestas a stdout.
3. WHEN el MCP_Server recibe una señal de terminación o EOF en stdin, THE MCP_Server SHALL cerrar las conexiones de AWS y terminar limpiamente.

### Requisito 6: Soporte de transporte Streamable HTTP

**Historia de Usuario:** Como usuario, quiero poder ejecutar el MCP Server como servicio HTTP remoto, para que pueda compartirlo entre múltiples clientes o desplegarlo en un servidor.

#### Criterios de Aceptación

1. WHERE el usuario configura transporte HTTP, THE MCP_Server SHALL exponer un endpoint HTTP Streamable compatible con el protocolo MCP.
2. WHERE el usuario configura transporte HTTP, THE MCP_Server SHALL aceptar un parámetro de puerto configurable.
3. WHERE el usuario configura transporte HTTP, THE MCP_Server SHALL manejar múltiples conexiones concurrentes de clientes MCP.

### Requisito 7: Configuración de credenciales AWS

**Historia de Usuario:** Como usuario, quiero que el servidor use la cadena estándar de credenciales de AWS, para que funcione con mis credenciales existentes sin configuración especial.

#### Criterios de Aceptación

1. THE MCP_Server SHALL utilizar la cadena estándar de credenciales de boto3 (variables de entorno, archivo de credenciales, perfil de instancia, etc.).
2. WHERE el usuario especifica un perfil AWS mediante variable de entorno o argumento, THE MCP_Server SHALL usar ese perfil para crear la sesión de boto3.
3. WHERE el usuario especifica una región AWS mediante variable de entorno o argumento, THE MCP_Server SHALL usar esa región para las llamadas a la API.
4. IF las credenciales de AWS no están configuradas o son inválidas, THEN THE MCP_Server SHALL reportar un error claro al intentar ejecutar la primera operación.

### Requisito 8: Manejo de paginación en operaciones de listado

**Historia de Usuario:** Como usuario, quiero que las operaciones de listado manejen la paginación automáticamente, para que obtenga resultados completos sin tener que paginar manualmente.

#### Criterios de Aceptación

1. WHEN un Cliente_MCP invoca una Tool de listado que retorna resultados paginados, THE MCP_Server SHALL retornar la primera página de resultados junto con el token de paginación si existe.
2. WHERE el Cliente_MCP proporciona un token de paginación como parámetro, THE MCP_Server SHALL usarlo para obtener la página siguiente de resultados.

### Requisito 9: Empaquetado y distribución del proyecto

**Historia de Usuario:** Como desarrollador que quiere usar el servidor, quiero instalarlo fácilmente desde PyPI o desde el repositorio, para que pueda integrarlo rápidamente en mi entorno.

#### Criterios de Aceptación

1. THE proyecto SHALL incluir un archivo `pyproject.toml` con metadatos completos (nombre, versión, dependencias, entry points).
2. THE proyecto SHALL definir un entry point de consola que permita ejecutar el servidor con un comando como `sagemaker-catalog-mcp-server`.
3. THE proyecto SHALL declarar como dependencias: `mcp`, `boto3`, y `botocore`.
4. THE proyecto SHALL ser instalable con `pip install .` desde el directorio raíz del repositorio.

### Requisito 10: Conversión de nombres de operaciones

**Historia de Usuario:** Como usuario del MCP Server, quiero que los nombres de las tools sigan una convención consistente y legible, para que pueda identificar fácilmente qué operación ejecuta cada tool.

#### Criterios de Aceptación

1. WHEN el Generador convierte un nombre de operación a nombre de Tool, THE Generador SHALL transformar PascalCase a snake_case (ej: `ListDomains` → `list_domains`).
2. THE Generador SHALL producir nombres de Tool únicos para cada operación del Service_Model.
3. WHEN el Generador convierte un nombre y luego lo revierte a PascalCase, THE Generador SHALL obtener el nombre original de la operación (propiedad round-trip).

### Requisito 11: Compatibilidad con el MCP Server existente

**Historia de Usuario:** Como usuario del Server_Existente, quiero que el nuevo MCP Server sea un reemplazo directo (drop-in replacement), para que pueda migrar sin cambiar la configuración de mi cliente MCP.

#### Criterios de Aceptación

1. THE MCP_Server SHALL exponer tools con los mismos nombres snake_case que el Server_Existente para las 49 operaciones que este cubre.
2. WHEN un Cliente_MCP invoca una Tool que existía en el Server_Existente con los mismos parámetros, THE MCP_Server SHALL producir una respuesta equivalente.
3. THE MCP_Server SHALL aceptar la misma configuración de ejecución (variables de entorno, argumentos) que el Server_Existente para las funcionalidades compartidas.

### Requisito 12: Auto-actualización con nuevas versiones de boto3

**Historia de Usuario:** Como mantenedor del proyecto, quiero que el servidor se actualice automáticamente cuando AWS agrega nuevas operaciones a DataZone, para que solo necesite actualizar la dependencia de boto3.

#### Criterios de Aceptación

1. WHEN se actualiza la versión de boto3/botocore y el Service_Model contiene nuevas operaciones, THE Generador SHALL generar tools para las nuevas operaciones sin cambios en el código del servidor.
2. WHEN se actualiza la versión de boto3/botocore y el Service_Model modifica shapes existentes, THE Generador SHALL reflejar los cambios en los esquemas de parámetros de las tools afectadas.
3. THE Generador SHALL depender exclusivamente del Service_Model de botocore como fuente de verdad para las definiciones de operaciones.

### Requisito 13: Suite de tests automatizados

**Historia de Usuario:** Como contribuidor del proyecto open-source, quiero una suite de tests completa, para que pueda verificar que mis cambios no rompen funcionalidad existente.

#### Criterios de Aceptación

1. THE proyecto SHALL incluir tests unitarios para el Generador que verifiquen la correcta extracción de operaciones, shapes y tipos del Service_Model.
2. THE proyecto SHALL incluir tests unitarios para la conversión de nombres de operaciones (PascalCase a snake_case y viceversa).
3. THE proyecto SHALL incluir tests unitarios para la conversión de tipos de botocore a JSON Schema.
4. THE proyecto SHALL incluir tests que verifiquen que el número de tools generadas coincide con el número de operaciones en el Service_Model.
5. THE proyecto SHALL incluir tests para el manejo de errores (Service_Model no encontrado, credenciales inválidas, errores de API).
6. THE proyecto SHALL ser ejecutable con `pytest` desde el directorio raíz del repositorio.
