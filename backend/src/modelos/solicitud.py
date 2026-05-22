"""Modelos Pydantic del agregado Solicitud (HU04).

Define los DTOs y entidades del flujo "Envio de solicitud a dependencia":
el usuario autenticado registra una solicitud dirigida a una dependencia,
con fecha de ingreso, fecha maxima de respuesta y estado inicial
``Pendiente``. Las invariantes (longitudes minimas, ventana temporal valida,
estados permitidos) se aplican aqui para que la capa de servicios reciba
datos ya consistentes.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Annotated
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

DETALLE_MIN_LENGTH: int = 10
DETALLE_MAX_LENGTH: int = 2000
USUARIO_ID_MIN_LENGTH: int = 1
USUARIO_ID_MAX_LENGTH: int = 64


class EstadoSolicitud(str, Enum):
    """Estados validos del ciclo de vida de una solicitud."""

    PENDIENTE = "Pendiente"
    EN_PROCESO = "En Proceso"
    ATENDIDA = "Atendida"
    RECHAZADA = "Rechazada"


class Dependencia(str, Enum):
    """Dependencias internas elegibles como destinatarias."""

    MESA_DE_PARTES = "MesaDePartes"
    TRAMITE_DOCUMENTARIO = "TramiteDocumentario"
    ASESORIA_LEGAL = "AsesoriaLegal"
    RECURSOS_HUMANOS = "RecursosHumanos"
    LOGISTICA = "Logistica"
    TESORERIA = "Tesoreria"
    SECRETARIA_GENERAL = "SecretariaGeneral"


def _ahora_utc() -> datetime:
    """Devuelve un ``datetime`` aware en UTC (evita fechas naive)."""
    return datetime.now(tz=timezone.utc)


def _nuevo_id() -> str:
    """Genera un identificador unico hex (UUID4) para una solicitud."""
    return uuid4().hex


class SolicitudInput(BaseModel):
    """Payload de entrada para registrar una nueva solicitud (HU04)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    usuario_id: Annotated[
        str,
        Field(
            min_length=USUARIO_ID_MIN_LENGTH,
            max_length=USUARIO_ID_MAX_LENGTH,
            description="Identificador del usuario autenticado emisor.",
        ),
    ]
    detalle_solicitud: Annotated[
        str,
        Field(
            min_length=DETALLE_MIN_LENGTH,
            max_length=DETALLE_MAX_LENGTH,
            description="Descripcion textual del asunto de la solicitud.",
        ),
    ]
    dependencia_asignada: Annotated[
        Dependencia,
        Field(description="Dependencia destinataria que debe atender el caso."),
    ]
    fecha_maxima_respuesta: Annotated[
        datetime,
        Field(
            description=(
                "Fecha limite (UTC) en la que la dependencia debe responder."
            ),
        ),
    ]


class Solicitud(BaseModel):
    """Entidad de dominio persistible para una solicitud ingresada."""

    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=False)

    id: Annotated[
        str,
        Field(
            default_factory=_nuevo_id,
            min_length=1,
            description="Identificador unico de la solicitud.",
        ),
    ]
    usuario_id: Annotated[
        str,
        Field(
            min_length=USUARIO_ID_MIN_LENGTH,
            max_length=USUARIO_ID_MAX_LENGTH,
        ),
    ]
    detalle_solicitud: Annotated[
        str,
        Field(
            min_length=DETALLE_MIN_LENGTH,
            max_length=DETALLE_MAX_LENGTH,
        ),
    ]
    dependencia_asignada: Dependencia
    fecha_ingreso: Annotated[
        datetime,
        Field(default_factory=_ahora_utc),
    ]
    fecha_maxima_respuesta: datetime
    estado: Annotated[
        EstadoSolicitud,
        Field(default=EstadoSolicitud.PENDIENTE),
    ]

    @model_validator(mode="after")
    def _validar_ventana_temporal(self) -> "Solicitud":
        """Garantiza que la fecha maxima sea posterior al ingreso."""
        if self.fecha_maxima_respuesta <= self.fecha_ingreso:
            raise ValueError(
                "fecha_maxima_respuesta debe ser posterior a fecha_ingreso."
            )
        return self


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


OBSERVACIONES_MAX_LENGTH: int = 500


class DerivacionInput(BaseModel):
    """Payload del administrador para derivar una solicitud (HU04).

    El administrador identifica al usuario y el detalle, escoge la
    dependencia destino y opcionalmente registra observaciones. La
    ``fecha_maxima_respuesta`` NO se acepta del cliente: la calcula la
    capa de servicios por norma (30 dias habiles).
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    usuario_id: Annotated[
        str,
        Field(
            min_length=USUARIO_ID_MIN_LENGTH,
            max_length=USUARIO_ID_MAX_LENGTH,
            description="Identificador del usuario emisor (ciudadano).",
        ),
    ]
    detalle_solicitud: Annotated[
        str,
        Field(
            min_length=DETALLE_MIN_LENGTH,
            max_length=DETALLE_MAX_LENGTH,
            description="Descripcion textual del asunto de la solicitud.",
        ),
    ]
    dependencia_asignada: Annotated[
        Dependencia,
        Field(description="Dependencia destinataria que debe atender el caso."),
    ]
    observaciones: Annotated[
        str,
        Field(
            default="",
            max_length=OBSERVACIONES_MAX_LENGTH,
            description="Notas internas del administrador sobre la derivacion.",
        ),
    ] = ""


class SolicitudDerivada(BaseModel):
    """Respuesta del endpoint de derivacion (HU04).

    Aplana los campos de auditoria que un administrador necesita ver tras
    una derivacion exitosa: identificador, dependencia destino, fechas
    calculadas y estado resultante.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    usuario_id: str
    detalle_solicitud: str
    dependencia_asignada: Dependencia
    fecha_ingreso: datetime
    fecha_maxima_respuesta: datetime
    estado: EstadoSolicitud
    observaciones: str = ""
