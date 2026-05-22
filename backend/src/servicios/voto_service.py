"""Servicio de dominio para el registro y auditoria de votos.

Encapsula la logica de negocio: orquesta el algoritmo genetico, el cifrado y
el repositorio en memoria. La capa de rutas debe limitarse a invocar este
servicio (Separation of Concerns / SRP).
"""

from __future__ import annotations

import time
from functools import lru_cache
from threading import Lock

from src.excepciones.errors import VotoDuplicadoError
from src.logging_config import get_logger
from src.modelos.voto import VotoCifrado, VotoInput
from src.utilidades.algoritmo_genetico import obtener_algoritmo
from src.utilidades.cifrado import aplicar_hash_sha256

logger = get_logger(__name__)


class VotoService:
    """Coordina el registro de votos cifrados.

    Mantiene un repositorio en memoria (thread-safe) que en produccion seria
    reemplazado por una base de datos persistente. La interfaz publica del
    servicio permanece igual gracias al principio de inversion de
    dependencias.
    """

    def __init__(self, algoritmo: AlgoritmoGenetico) -> None:
        self._algoritmo: AlgoritmoGenetico = algoritmo
        self._votos: list[VotoCifrado] = []
        self._hashes: set[str] = set()
        self._lock: Lock = Lock()

    def registrar_voto(self, voto: VotoInput) -> VotoCifrado:
        """Registra un voto generando llave evolutiva y hash SHA-256.

        Args:
            voto: Datos del voto entrante ya validados por Pydantic.

        Returns:
            Comprobante cifrado anonimo del voto.

        Raises:
            VotoDuplicadoError: Si el hash resultante ya existe en el
                repositorio (colision o intento de duplicar voto).
        """
        llave: str = self._algoritmo.generar_llave()
        hash_voto: str = aplicar_hash_sha256(
            dni=voto.dni_votante,
            candidato=voto.id_candidato,
            llave=llave,
        )
        comprobante: VotoCifrado = VotoCifrado(
            hash_voto=hash_voto,
            clave_genetica=llave,
            timestamp=time.time(),
        )
        with self._lock:
            if hash_voto in self._hashes:
                raise VotoDuplicadoError(
                    "El comprobante generado ya existe; reintente."
                )
            self._hashes.add(hash_voto)
            self._votos.append(comprobante)
        logger.info(
            "Voto registrado | candidato=%d | total_votos=%d",
            voto.id_candidato,
            len(self._votos),
        )
        return comprobante

    def listar_votos(self) -> list[VotoCifrado]:
        """Devuelve una copia inmutable de los votos cifrados."""
        with self._lock:
            return list(self._votos)


@lru_cache(maxsize=1)
def get_voto_service() -> VotoService:
    """Provee una instancia singleton del servicio (DI para FastAPI)."""
    return VotoService(algoritmo=obtener_algoritmo())
