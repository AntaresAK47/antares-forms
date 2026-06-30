# =============================================================
# ANTARES FORMS — Motor de Personas Virtuales
# Archivo: src/persona_engine.py
# Descripción: Genera perfiles humanos virtuales con lógica
#              interna coherente para simular respuestas reales.
# =============================================================

from __future__ import annotations

import random
from dataclasses import dataclass

from faker import Faker

# Faker en español para nombres latinos.
fake = Faker("es_ES")

# Catálogos de valores posibles (constantes nombradas).
PERSONALIDADES = ["optimista", "pesimista", "neutral", "practico", "emocional"]
REGIONES = ["Norte", "Sur", "Centro", "Este", "Oeste",
            "Capital", "Interior", "Costa", "Sierra", "Valle"]


@dataclass
class Persona:
    """Persona virtual con un perfil coherente que sesga sus respuestas."""
    nombre: str
    edad: int
    grupo_edad: str       # joven | adulto | maduro | mayor
    genero: str           # masculino | femenino
    educacion: str        # basico | medio | universitario | posgrado
    economia: str         # bajo | medio | alto
    personalidad: str     # ver PERSONALIDADES
    region: str           # zona geográfica simulada

    def __str__(self) -> str:
        return (
            f"{self.nombre} | {self.edad} años | {self.genero} | "
            f"Educación: {self.educacion} | Economía: {self.economia} | "
            f"Personalidad: {self.personalidad}"
        )


def _clasificar_edad(edad: int) -> str:
    if edad <= 25:
        return "joven"
    if edad <= 40:
        return "adulto"
    if edad <= 55:
        return "maduro"
    return "mayor"


def _educacion_por_grupo(grupo: str) -> str:
    tabla = {
        "joven":  (["basico", "medio", "universitario"], [10, 45, 45]),
        "adulto": (["basico", "medio", "universitario", "posgrado"], [10, 30, 40, 20]),
        "maduro": (["basico", "medio", "universitario", "posgrado"], [20, 35, 30, 15]),
        "mayor":  (["basico", "medio", "universitario", "posgrado"], [35, 40, 20, 5]),
    }
    opciones, pesos = tabla[grupo]
    return random.choices(opciones, weights=pesos, k=1)[0]


def _personalidad_por_economia(economia: str) -> str:
    tabla = {
        "alto":  [40, 5, 25, 25, 5],
        "bajo":  [15, 30, 25, 20, 10],
        "medio": [25, 15, 30, 20, 10],
    }
    return random.choices(PERSONALIDADES, weights=tabla[economia], k=1)[0]


def generar_persona() -> Persona:
    """
    Crea una persona virtual con atributos aleatorios pero coherentes:
    la edad condiciona la educación y la economía condiciona la
    personalidad, imitando correlaciones reales de una población.
    """
    # Edad con distribución realista (más densidad en 26-40).
    edad = random.choices(
        population=list(range(18, 71)),
        weights=[*[8] * 8, *[10] * 15, *[7] * 15, *[3] * 15],
        k=1,
    )[0]

    grupo_edad = _clasificar_edad(edad)

    genero = random.choices(["masculino", "femenino"], weights=[48, 52], k=1)[0]
    nombre = fake.name_male() if genero == "masculino" else fake.name_female()

    educacion = _educacion_por_grupo(grupo_edad)
    economia = random.choices(["bajo", "medio", "alto"], weights=[38, 47, 15], k=1)[0]
    personalidad = _personalidad_por_economia(economia)
    region = random.choice(REGIONES)

    return Persona(
        nombre=nombre,
        edad=edad,
        grupo_edad=grupo_edad,
        genero=genero,
        educacion=educacion,
        economia=economia,
        personalidad=personalidad,
        region=region,
    )


def generar_grupo(cantidad: int) -> list[Persona]:
    """Genera una lista de 'cantidad' personas virtuales."""
    return [generar_persona() for _ in range(cantidad)]


# -------------------------------------------------------------
# Prueba directa: python3 -m src.persona_engine
# -------------------------------------------------------------
if __name__ == "__main__":
    from rich.console import Console
    from rich.table import Table

    console = Console()
    console.print("\n[bold cyan]⚗️  ANTARES FORMS — Motor de Personas[/bold cyan]")
    console.print("[dim]Generando 10 personas virtuales de prueba…[/dim]\n")

    tabla = Table(title="👥 Personas Virtuales", header_style="bold magenta")
    tabla.add_column("Nº", style="dim", width=4)
    tabla.add_column("Nombre", style="cyan", width=22)
    tabla.add_column("Edad", justify="center", width=6)
    tabla.add_column("Género", width=12)
    tabla.add_column("Educación", width=14)
    tabla.add_column("Economía", width=10)
    tabla.add_column("Personalidad", width=12)

    for i, p in enumerate(generar_grupo(10), 1):
        tabla.add_row(str(i), p.nombre, str(p.edad), p.genero,
                      p.educacion, p.economia, p.personalidad)

    console.print(tabla)
    console.print("\n[green]✅ 10 personas generadas correctamente.[/green]\n")
