# Business Chat Process

## Objetivo

`/business-chat` expone un pipeline que:

1. recibe una consulta de negocio,
2. resuelve una skill segun `intent_type`,
3. descubre que capabilities reales puede usar,
4. le pide a un LLM que arme un plan,
5. ejecuta ese plan contra FastFixPro,
6. empaqueta los datos obtenidos,
7. genera un reporte final con otro LLM,
8. valida la salida antes de responder.

La idea central es separar:

- descubrimiento de capacidades reales,
- planificacion con LLM,
- ejecucion controlada,
- generacion del reporte final,
- validacion estructural de la salida.

## Punto de entrada

El endpoint esta en `src/api/routes/business_chat.py`.

### Request

`BusinessChatRequest` recibe:

- `intent_type`: hoy soporta `business_report` y `marketing_plan`
- `question`: texto obligatorio
- `params`: diccionario opcional

### Response

`BusinessChatResponse` devuelve:

- `request_id`
- `intent_type`
- `report`
- `data_quality`
- `warnings`

## Flujo end-to-end

### 1. Validacion HTTP y creacion del comando

FastAPI valida el body con Pydantic. Si el request es valido, la ruta:

- genera un `request_id` con `uuid4()`
- construye un `BusinessChatCommand`
- delega todo al caso de uso `RunBusinessChatUseCase`

Si `intent_type` no existe o `question` esta vacia, FastAPI responde `422` antes de entrar al pipeline.

### 2. Inyeccion de dependencias

`src/api/dependencies.py` arma el caso de uso con estas piezas:

- `YamlSkillRepository`
- `FastFixProCapabilityGateway`
- `AgentFrameworkPlanner`
- `AgentFrameworkReportGenerator`

Las dependencias estan cacheadas con `@lru_cache`, asi que se reutilizan entre requests.

### 3. Resolucion de la skill

El caso de uso busca una definicion YAML en:

`src/infrastructure/skills/definitions/{intent_type}.yaml`

La skill define:

- nombre y descripcion
- idioma
- prompt del planner
- limite maximo de capabilities
- prompt del generador de reporte
- secciones esperadas
- `output_schema`
- restricciones de negocio

Si no existe el archivo o no valida contra `SkillDefinition`, se lanza `SkillNotFound` y el endpoint responde `404`.

### 4. Descubrimiento de capabilities

`run_discovery()` llama a `gateway.discover()`.

`FastFixProCapabilityGateway` usa un catalogo compartido (`src/mcp/catalog.py`) que:

- consulta `GET /api/agent-capabilities` en FastFixPro,
- usa `FASTFIXPRO_API_BASE_URL` y `FASTFIXPRO_API_TOKEN`,
- cachea el catalogo por 5 minutos.

El resultado se transforma en una lista de `CapabilityDescriptor` con:

- `id`
- `description`
- `params`

Esto define el universo real de cosas que el planner puede pedir.

### 5. Planificacion con LLM

`run_planning()` llama a `AgentFrameworkPlanner`.

El planner recibe:

- la pregunta del usuario,
- el `intent_type`,
- la skill,
- el catalogo descubierto.

El prompt incluye:

- el `system_prompt` de la skill,
- la lista serializada de capabilities disponibles,
- las restricciones,
- el limite `max_capabilities`,
- el formato JSON exacto esperado.

La salida esperada es:

```json
{
  "items": [
    {
      "capability_id": "get_sales",
      "reason": "por que hace falta",
      "params": {
        "month": 4
      }
    }
  ]
}
```

Si el planner no devuelve JSON valido o no cumple el schema `CapabilityPlan`, se lanza `PlanningError` y el endpoint responde `502`.

### 6. Validacion anti-hallucination del plan

`validate_plan()` aplica una compuerta deterministica antes de ejecutar nada:

- conserva solo `capability_id` presentes en el catalogo descubierto,
- descarta capabilities inventadas por el LLM,
- recorta la lista final a `skill.planner.max_capabilities`.

Las capabilities descartadas no rompen el request: quedan registradas en `warnings`.

### 7. Ejecucion de capabilities

`run_execution()` recorre el plan validado y ejecuta cada item en secuencia.

Reglas actuales del gateway:

- solo se ejecutan capabilities `GET`
- solo se envian params definidos en el catalogo
- params desconocidos se descartan
- si faltan params requeridos, esa capability falla

Cada resultado se guarda como `ExecutionResult` con estado:

- `success`
- `failed`

Una falla parcial no aborta el pipeline. Se registra el error y se sigue con el resto.

### 8. Armado del context pack

`build_context_pack()` transforma los resultados crudos en una estructura limpia:

- `available_data`: solo incluye capabilities exitosas
- `data_quality`: resume cantidad pedida, exitosa, fallida y completitud
- `business_context`: incluye intent, pregunta, skill, schema e idioma

La completitud se calcula como:

`succeeded / requested`

### 9. Generacion del reporte final

`run_report()` llama a `AgentFrameworkReportGenerator`.

Este segundo agente:

- no usa tools,
- trabaja solo con el `context_pack`,
- recibe el prompt definido por la skill,
- debe devolver JSON con las secciones esperadas.

Para `business_report`, el schema esperado hoy es:

- `resumen`
- `hallazgos`
- `recomendaciones`
- `limitations`

Para `marketing_plan`:

- `objetivos`
- `segmentos`
- `acciones`
- `metricas`
- `limitations`

### 10. Validacion y reparacion de salida

`validate_and_repair()` toma `skill.output_schema` y busca el modelo Pydantic asociado en `src/application/dtos/report_schemas.py`.

Comportamiento:

1. valida la primera respuesta del LLM
2. si falla, hace un solo intento de reparacion pasando feedback del error
3. si vuelve a fallar, lanza `OutputValidationError`

Ese error termina en HTTP `422`.

### 11. Respuesta final

Si todo sale bien, el caso de uso devuelve:

- `request_id`
- `intent_type`
- `report`
- `data_quality`
- `warnings`

Los warnings hoy cubren dos casos:

- capabilities descartadas por no existir en el catalogo
- capabilities que fallaron durante la ejecucion

## Mapeo de errores HTTP

- `404`: no existe una skill para el `intent_type`
- `422`: request invalido o reporte final invalido luego del repair
- `502`: fallo del planner o fallo inesperado en dependencias upstream
- `500`: `ApplicationError` generico

Ademas, el endpoint siempre intenta devolver un `request_id` dentro de `detail` para facilitar trazabilidad.

## Observaciones importantes del comportamiento actual

### `params` del request no participan del pipeline

`BusinessChatRequest` acepta `params` y la ruta los copia a `BusinessChatCommand`, pero hoy el caso de uso no los usa en:

- planning,
- ejecucion,
- generacion del reporte.

En la implementacion actual, los params efectivos salen del plan generado por el LLM, no del `params` que envia el cliente.

### El reporte solo ve datos exitosos

Las capabilities fallidas no aparecen en `available_data`. Su efecto entra solo por:

- `data_quality`
- `warnings`
- la instruccion de completar `limitations`

### La ejecucion es tolerante a fallas parciales

Un request puede responder `200` aunque una o varias capabilities fallen, siempre que el reporte final siga pudiendo generarse y validar.

## Archivos clave

- `src/api/routes/business_chat.py`: endpoint y mapeo de errores HTTP
- `src/api/dependencies.py`: wiring de dependencias
- `src/application/use_cases/run_business_chat.py`: orquestacion completa
- `src/application/pipeline/*.py`: pasos del pipeline
- `src/infrastructure/skills/definitions/*.yaml`: configuracion por intent
- `src/infrastructure/skills/yaml_skill_repository.py`: carga de skills
- `src/mcp/catalog.py`: descubrimiento y cache del catalogo
- `src/infrastructure/capabilities/capability_gateway.py`: ejecucion real contra FastFixPro
- `src/infrastructure/agents/agent_framework_planner.py`: planner LLM
- `src/infrastructure/agents/agent_framework_report.py`: generador final del reporte
- `src/application/dtos/report_schemas.py`: validacion estructural de salida

## Resumen corto

`business_chat` no llama directamente a endpoints fijos ni deja que el LLM ejecute libremente. Primero descubre un catalogo real, despues usa el LLM solo para planificar y redactar, y en el medio aplica controles deterministas para evitar capabilities inventadas y para validar la estructura final de la respuesta.
