"""Simulacion didactica de un algoritmo genetico para generar llaves.

El algoritmo NO es un sustituto de un PRNG criptografico: solo ilustra,
para fines academicos, como un proceso evolutivo (poblacion -> seleccion ->
cruce -> mutacion) puede usarse para producir llaves variables que luego
acompanan al hash SHA-256 del voto.

Las clases siguen una unica responsabilidad cada una (SRP) y se inyectan
entre si para facilitar pruebas y reemplazo (DIP).
"""

from __future__ import annotations

import secrets
import string
from dataclasses import dataclass
from functools import lru_cache
from typing import Final

_ALFABETO: Final[str] = string.ascii_uppercase
_RNG: Final[secrets.SystemRandom] = secrets.SystemRandom()


@dataclass(frozen=True, slots=True)
class Cromosoma:
    """Representa una llave candidata como secuencia de caracteres.

    Attributes:
        genes: Cadena de letras mayusculas que conforman la llave.
    """

    genes: str

    def __str__(self) -> str:  # pragma: no cover - representacion trivial
        return self.genes

    @classmethod
    def aleatorio(cls, longitud: int) -> "Cromosoma":
        """Crea un cromosoma aleatorio usando un PRNG criptografico.

        Args:
            longitud: Cantidad de genes (caracteres) que tendra la llave.

        Returns:
            Una instancia ``Cromosoma`` con ``longitud`` genes.
        """
        genes: str = "".join(_RNG.choice(_ALFABETO) for _ in range(longitud))
        return cls(genes=genes)


@dataclass(frozen=True, slots=True)
class Poblacion:
    """Coleccion de cromosomas que evolucionan en cada generacion."""

    individuos: tuple[Cromosoma, ...]

    @classmethod
    def inicial(cls, tamano: int, longitud_gen: int) -> "Poblacion":
        """Genera una poblacion inicial con cromosomas aleatorios."""
        if tamano < 2:
            raise ValueError("La poblacion debe tener al menos 2 individuos.")
        individuos = tuple(
            Cromosoma.aleatorio(longitud_gen) for _ in range(tamano)
        )
        return cls(individuos=individuos)

    def seleccionar_padres(self) -> tuple[Cromosoma, Cromosoma]:
        """Selecciona dos padres distintos uniformemente al azar."""
        padre1, padre2 = _RNG.sample(self.individuos, k=2)
        return padre1, padre2


class Cruce:
    """Operador de cruce de un solo punto (single-point crossover)."""

    @staticmethod
    def aplicar(padre1: Cromosoma, padre2: Cromosoma) -> Cromosoma:
        """Combina dos padres tomando la mitad de cada uno.

        Args:
            padre1: Primer cromosoma progenitor.
            padre2: Segundo cromosoma progenitor.

        Returns:
            Cromosoma hijo resultante del cruce.

        Raises:
            ValueError: Si los padres tienen longitudes distintas.
        """
        if len(padre1.genes) != len(padre2.genes):
            raise ValueError("Los padres deben tener la misma longitud.")
        punto: int = len(padre1.genes) // 2
        genes_hijo: str = padre1.genes[:punto] + padre2.genes[punto:]
        return Cromosoma(genes=genes_hijo)


@dataclass(frozen=True, slots=True)
class Mutacion:
    """Operador de mutacion puntual con tasa configurable."""

    tasa: float

    def aplicar(self, cromosoma: Cromosoma) -> Cromosoma:
        """Reemplaza cada gen con probabilidad ``tasa``.

        Args:
            cromosoma: Cromosoma a mutar.

        Returns:
            Nuevo cromosoma posiblemente mutado (instancia distinta).
        """
        if not 0.0 <= self.tasa <= 1.0:
            raise ValueError("La tasa de mutacion debe estar en [0, 1].")
        nuevos_genes: list[str] = []
        for gen in cromosoma.genes:
            if _RNG.random() < self.tasa:
                nuevos_genes.append(_RNG.choice(_ALFABETO))
            else:
                nuevos_genes.append(gen)
        return Cromosoma(genes="".join(nuevos_genes))


@dataclass(frozen=True, slots=True)
class AlgoritmoGenetico:
    """Coordinador del flujo evolutivo: poblacion -> cruce -> mutacion.

    Attributes:
        tamano_poblacion: Cantidad de individuos en la poblacion inicial.
        longitud_llave: Numero de caracteres por cromosoma.
        mutacion: Estrategia de mutacion inyectada.
    """

    tamano_poblacion: int
    longitud_llave: int
    mutacion: Mutacion

    def generar_llave(self) -> str:
        """Ejecuta una generacion del AG y devuelve la llave resultante.

        Returns:
            Cadena de letras mayusculas que representa la llave evolutiva.
        """
        poblacion: Poblacion = Poblacion.inicial(
            tamano=self.tamano_poblacion,
            longitud_gen=self.longitud_llave,
        )
        padre1, padre2 = poblacion.seleccionar_padres()
        hijo: Cromosoma = Cruce.aplicar(padre1, padre2)
        hijo_mutado: Cromosoma = self.mutacion.aplicar(hijo)
        return hijo_mutado.genes


@lru_cache(maxsize=1)
def obtener_algoritmo() -> AlgoritmoGenetico:
    from src.config import settings  # importacion diferida para evitar ciclos

    return AlgoritmoGenetico(
        tamano_poblacion=settings.ga_population_size,
        longitud_llave=settings.ga_key_length,
        mutacion=Mutacion(tasa=settings.ga_mutation_rate),
    )
