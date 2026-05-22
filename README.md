## 1. Singleton — `obtener_algoritmo()`

Modifiqué `backend/src/utilidades/algoritmo_genetico.py` afectando `backend/src/servicios/voto_service.py`

Agregué en `algoritmo_genetico.py` añadí la decoración `@lru_cache(maxsize=1)` en `obtener_algoritmo()`:

```python
@lru_cache(maxsize=1)
def obtener_algoritmo() -> AlgoritmoGenetico:
    from src.config import settings
    return AlgoritmoGenetico(
        tamano_poblacion=settings.ga_population_size,
        longitud_llave=settings.ga_key_length,
        mutacion=Mutacion(tasa=settings.ga_mutation_rate),
    )
```

modifiqué `get_voto_service()` en `voto_service.py` ya que pasó de construir el algoritmo internamente a dejarlo a `obtener_algoritmo()`:

```python
# antes
@lru_cache(maxsize=1)
def get_voto_service() -> VotoService:
    algoritmo = AlgoritmoGenetico(
        tamano_poblacion=settings.ga_population_size,
        longitud_llave=settings.ga_key_length,
        mutacion=Mutacion(tasa=settings.ga_mutation_rate),
    )
    return VotoService(algoritmo=algoritmo)

# después
@lru_cache(maxsize=1)
def get_voto_service() -> VotoService:
    return VotoService(algoritmo=obtener_algoritmo())
```

Eliminé los imports `from src.config import settings`, `AlgoritmoGenetico` y `Mutacion` de `voto_service.py` porque ya no son necesarios principalmente debido a que `AlgoritmoGenetico` es stateless y crea la población inicial en cada construcción. Al usar `obtener_algoritmo()` como Singleton, la instancia se crea una sola vez y se reutiliza en toda la vida de la aplicación, igual que `get_voto_service()`, por lo que cada componente del backend tiene su propio punto de acceso singleton.


---

## 2. Factory Method — `SolicitudFactory`

Modifiqué `backend/src/modelos/solicitud.py`, afectando `backend/src/servicios/solicitud_service.py`

Luego, agregué la clase `SolicitudFactory` en `solicitud.py` antes de la definición de `DerivacionInput`:

```python
class SolicitudFactory:
    """Centraliza la construccion de entidades Solicitud."""

    @staticmethod
    def desde_derivacion(
        payload: DerivacionInput,
        fecha_ingreso: datetime,
        fecha_maxima_respuesta: datetime,
    ) -> Solicitud:
        return Solicitud(
            usuario_id=payload.usuario_id,
            detalle_solicitud=payload.detalle_solicitud,
            dependencia_asignada=payload.dependencia_asignada,
            fecha_ingreso=fecha_ingreso,
            fecha_maxima_respuesta=fecha_maxima_respuesta,
        )
```

El campo `estado` no se pasa porque `Solicitud` ya lo inicializa en `PENDIENTE` de manera por defecto.

Modifiqué `SolicitudService.derivar()` en `solicitud_service.py` donde reemplacé la construcción directa de `Solicitud` por la llamada al factory:

```python
# antes
solicitud: Solicitud = Solicitud(
    usuario_id=payload.usuario_id,
    detalle_solicitud=payload.detalle_solicitud,
    dependencia_asignada=payload.dependencia_asignada,
    fecha_ingreso=ahora,
    fecha_maxima_respuesta=fecha_maxima,
    estado=EstadoSolicitud.PENDIENTE,
)

# después
solicitud: Solicitud = SolicitudFactory.desde_derivacion(
    payload=payload,
    fecha_ingreso=ahora,
    fecha_maxima_respuesta=fecha_maxima,
)
```

El import de `EstadoSolicitud` se eliminó de `solicitud_service.py` y se incorporó `SolicitudFactory` porque antes, la lógica cuando se queria saber los campos que llevaria Solicitud recien derivada estaba estaba repartida entre el servicio que construía el objeto y el modelo que definía los defaults. El Factory Method hace que esta decisión se haga en un único lugar dentro del módulo de modelos. 

Este patrón ya existía en el proyecto como `Cromosoma.aleatorio()` y `Poblacion.inicial()`, por lo que `SolicitudFactory` extiende esto a las solicitudes.
