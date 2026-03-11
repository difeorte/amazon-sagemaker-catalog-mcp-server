# Plan de Implementación: SageMaker Catalog MCP Server

## Visión General

Implementación incremental del MCP server que auto-genera tools desde el service model de botocore. Se construye de abajo hacia arriba: primero las utilidades de conversión, luego el parser, el generador, el executor, y finalmente el servidor MCP que integra todo.

## Tareas

- [x] 1. Configurar estructura del proyecto y dependencias
  - [x] 1.1 Crear estructura de directorios y `pyproject.toml`
    - Crear `src/sagemaker_catalog_mcp_server/__init__.py`, `server.py`, `generator.py`, `utils/__init__.py`
    - Configurar `pyproject.toml` con nombre `amazon-sagemaker-catalog-mcp-server`, dependencias (`mcp`, `boto3`, `botocore`), dev dependencies (`pytest`, `hypothesis`, `pytest-mock`), y entry point de consola `sagemaker-catalog-mcp-server`
    - Crear `tests/conftest.py` con fixtures básicos (service model de ejemplo mínimo)
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

- [x] 2. Implementar NameConverter (conversión PascalCase ↔ snake_case)
  - [x] 2.1 Implementar `NameConverter` en `src/sagemaker_catalog_mcp_server/utils/name_converter.py`
    - Método `to_snake_case(pascal_name: str) -> str` que maneja acrónimos (ej: `GetIAMPolicy` → `get_iam_policy`)
    - Método `to_pascal_case(snake_name: str) -> str` como inverso
    - _Requirements: 10.1, 10.3, 2.2_
  - [x] 2.2 Escribir property test para round-trip de nombres
    - **Property 2: Round-trip de conversión de nombres PascalCase ↔ snake_case**
    - **Validates: Requirements 10.3, 10.1, 2.2**
  - [x] 2.3 Escribir unit tests para NameConverter
    - Casos conocidos de la API de DataZone: `ListDomains`, `CreateAssetType`, `GetIAMPortalLoginUrl`
    - Edge cases: nombres de una sola palabra, acrónimos consecutivos
    - _Requirements: 13.2_

- [x] 3. Implementar ServiceModelParser (lectura y parseo del service model)
  - [x] 3.1 Implementar dataclasses `ShapeInfo`, `MemberInfo`, `OperationInfo`, `ServiceModel` en `src/sagemaker_catalog_mcp_server/models.py`
    - Definir todas las dataclasses según el diseño
    - _Requirements: 1.2, 1.3_
  - [x] 3.2 Implementar `ServiceModelParser` en `src/sagemaker_catalog_mcp_server/parser.py`
    - Método `find_service_model_path()` que localiza `service-2.json` de DataZone en botocore
    - Método `parse(service_model_path: str | None = None) -> ServiceModel` que lee y parsea el JSON
    - Extraer operaciones, shapes (structure, list, map, primitivos), miembros, required fields, enums, documentación
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_
  - [x] 3.3 Escribir property test para round-trip del parseo
    - **Property 1: Round-trip del parseo del Service Model**
    - **Validates: Requirements 1.6**
  - [x] 3.4 Escribir property test para completitud de extracción de miembros
    - **Property 4: Completitud de extracción de miembros de shapes structure**
    - **Validates: Requirements 1.3**
  - [x] 3.5 Escribir unit tests para ServiceModelParser
    - Parseo de service model mínimo, manejo de shapes vacíos, error cuando no se encuentra el archivo
    - _Requirements: 13.1, 13.5_

- [x] 4. Checkpoint - Verificar que parser y name converter funcionan
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implementar TypeConverter (conversión de tipos botocore a JSON Schema)
  - [x] 5.1 Implementar `TypeConverter` en `src/sagemaker_catalog_mcp_server/utils/type_converter.py`
    - Conversión de todos los tipos primitivos (string, integer, long, float, double, boolean, timestamp, blob)
    - Conversión de string con enum a JSON Schema con `enum`
    - Conversión de structure a object con properties y required
    - Conversión de list a array con items
    - Conversión de map a object con additionalProperties
    - Resolución recursiva con detección de ciclos
    - _Requirements: 2.5, 1.4_
  - [x] 5.2 Escribir property test para conversión de tipos
    - **Property 7: Conversión de tipos botocore a JSON Schema**
    - **Validates: Requirements 2.5**
  - [x] 5.3 Escribir property test para resolución recursiva de shapes anidados
    - **Property 5: Resolución recursiva de shapes anidados**
    - **Validates: Requirements 1.4**
  - [x] 5.4 Escribir unit tests para TypeConverter
    - Cada tipo primitivo, structures anidadas, listas de listas, maps, enums, shapes con ciclos
    - _Requirements: 13.3_

- [x] 6. Implementar ToolGenerator (generación de tool definitions)
  - [x] 6.1 Implementar dataclass `ToolDefinition` en `src/sagemaker_catalog_mcp_server/models.py`
    - Campos: tool_name, operation_name, description, input_schema, required_params
    - _Requirements: 2.1_
  - [x] 6.2 Implementar `ToolGenerator` en `src/sagemaker_catalog_mcp_server/generator.py`
    - Método `generate_all() -> list[ToolDefinition]` que genera una tool por operación
    - Método `generate_tool(operation: OperationInfo) -> ToolDefinition` para una operación individual
    - Usar NameConverter para nombres y TypeConverter para esquemas
    - Extraer descripción de la documentación de la operación
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.6, 12.1, 12.2_
  - [x] 6.3 Escribir property test para conteo y unicidad de tools
    - **Property 3: Conteo y unicidad de tools generadas**
    - **Validates: Requirements 2.1, 2.6, 10.2, 12.1**
  - [x] 6.4 Escribir property test para fidelidad de tool definitions
    - **Property 6: Fidelidad de tool definitions respecto al Service Model**
    - **Validates: Requirements 2.3, 2.4**
  - [x] 6.5 Escribir unit tests para ToolGenerator
    - Generación con operaciones sin input shape, con shapes complejos, verificar que el número de tools coincide con operaciones
    - _Requirements: 13.1, 13.4_

- [x] 7. Checkpoint - Verificar que la cadena completa de generación funciona
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Implementar ToolExecutor (ejecución de operaciones contra AWS)
  - [x] 8.1 Implementar `ToolExecutor` en `src/sagemaker_catalog_mcp_server/executor.py`
    - Crear cliente boto3 de DataZone con soporte de región y perfil configurables
    - Método `execute(operation_name: str, parameters: dict) -> dict` que llama a boto3
    - Serialización de respuestas (datetime → ISO string, bytes → base64, Decimal → float, eliminar ResponseMetadata)
    - Manejo de errores: ClientError, EndpointConnectionError, timeout, credenciales
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 7.1, 7.2, 7.3, 7.4_
  - [x] 8.2 Escribir property test para serialización de respuestas
    - **Property 8: Serialización de respuestas boto3 a JSON**
    - **Validates: Requirements 4.2**
  - [x] 8.3 Escribir property test para errores de AWS estructurados
    - **Property 10: Errores de AWS se estructuran correctamente**
    - **Validates: Requirements 4.4**
  - [x] 8.4 Escribir property test para validación de parámetros
    - **Property 9: Validación rechaza entradas inválidas**
    - **Validates: Requirements 4.3**
  - [x] 8.5 Escribir unit tests para ToolExecutor
    - Mock de boto3 para verificar llamadas correctas, manejo de cada tipo de error, serialización de datetime/bytes/Decimal
    - _Requirements: 13.5_

- [x] 9. Implementar MCPServer (servidor principal con registro dinámico de tools)
  - [x] 9.1 Implementar `SageMakerCatalogMCPServer` en `src/sagemaker_catalog_mcp_server/server.py`
    - Inicialización: parsear service model → generar tools → registrar en FastMCP
    - Registro dinámico de cada tool con su handler que invoca al ToolExecutor
    - Soporte de transporte stdio (por defecto) y HTTP (configurable)
    - Configuración via variables de entorno y argumentos CLI (región, perfil, transporte, puerto)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 5.1, 5.2, 5.3, 6.1, 6.2, 6.3, 8.1, 8.2_
  - [x] 9.2 Implementar entry point CLI en `src/sagemaker_catalog_mcp_server/__main__.py`
    - Parseo de argumentos: `--transport` (stdio/http), `--port`, `--region`, `--profile`
    - Variables de entorno: `AWS_REGION`, `AWS_PROFILE`, `MCP_TRANSPORT`, `MCP_PORT`
    - _Requirements: 5.1, 6.1, 6.2, 7.2, 7.3, 9.2, 11.3_
  - [x] 9.3 Escribir unit tests para el servidor
    - Test de inicialización con service model real, verificar que se registran 176+ tools
    - Test de manejo de errores de inicialización
    - _Requirements: 3.1, 3.2, 11.1_

- [x] 10. Checkpoint - Verificar integración completa
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Documentación y archivos del proyecto
  - [x] 11.1 Crear README.md con instrucciones de instalación, configuración, y uso
    - Secciones: instalación, configuración de credenciales, uso con stdio, uso con HTTP, lista de tools disponibles, compatibilidad con server existente
    - _Requirements: 9.4, 11.3_
  - [x] 11.2 Crear archivo LICENSE (Apache 2.0)
    - _Requirements: 9.1_

- [x] 12. Checkpoint final - Verificar que todo funciona
  - Ensure all tests pass, ask the user if questions arise.

## Notas

- Las tareas marcadas con `*` son opcionales y pueden omitirse para un MVP más rápido
- Cada tarea referencia requisitos específicos para trazabilidad
- Los checkpoints aseguran validación incremental
- Los property tests validan propiedades universales de correctitud
- Los unit tests validan ejemplos específicos y edge cases
- El lenguaje de implementación es Python 3.11+ con hypothesis para property-based testing
