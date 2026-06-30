# =============================================================
# ANTARES FORMS — Motor de Respuestas (auditado)
# Archivo: src/response_engine.py
# Descripción: Genera respuestas lógicas y variadas para cada
#              persona virtual según su perfil interno.
#
# Tipos soportados (los que usa el formulario real):
#   - opcion_multiple : una opción de una lista
#   - escala          : número entre min y max (admite rango_forzado)
#   - checkboxes      : selección múltiple
#
# Nota de auditoría: se eliminaron los tipos 'si_no' y
# 'texto_abierto' junto con su banco de ~200 frases. Eran código
# muerto — el formulario de phishing no contiene preguntas de esos
# tipos. Si en el futuro se necesitan, conviene moverlos a un
# módulo aparte (p. ej. banco_frases.py) en lugar de inflar este.
# =============================================================

from __future__ import annotations

import random

from src.persona_engine import Persona


# -------------------------------------------------------------
# Despachador principal
# -------------------------------------------------------------
def responder_pregunta(persona: Persona, pregunta: dict) -> str:
    """
    Devuelve la respuesta (como texto) de 'persona' a 'pregunta',
    según el tipo declarado en la pregunta.
    """
    tipo = pregunta.get("tipo")
    if tipo == "opcion_multiple":
        return _responder_opcion_multiple(persona, pregunta)
    if tipo == "escala":
        return _responder_escala(persona, pregunta)
    if tipo == "checkboxes":
        return _responder_checkboxes(persona, pregunta)
    return "Sin respuesta"


# -------------------------------------------------------------
# Helper común de pesos por atributo
# -------------------------------------------------------------
def _pesos_por_atributo(persona: Persona, opciones: list, pesos: dict) -> list[int] | None:
    """
    Busca, en orden de prioridad (economía → educación → grupo de
    edad), una clave de 'pesos' que aplique a la persona y cuya
    longitud coincida con el número de opciones. Devuelve esos
    pesos, o None si ninguna clave aplica.
    """
    for atributo in (
        f"economia_{persona.economia}",
        f"educacion_{persona.educacion}",
        f"grupo_edad_{persona.grupo_edad}",
    ):
        valores = pesos.get(atributo)
        if valores and len(valores) == len(opciones):
            return valores
    return None


# -------------------------------------------------------------
# Tipo: opción múltiple
# -------------------------------------------------------------
def _responder_opcion_multiple(persona: Persona, pregunta: dict) -> str:
    """
    Elige una opción. Si la pregunta define 'pesos' por perfil, los
    aplica; si no, usa un sesgo suave según la personalidad.
    """
    opciones = pregunta.get("opciones", [])
    if not opciones:
        return "Sin opciones"

    pesos = pregunta.get("pesos")
    if pesos:
        valores = _pesos_por_atributo(persona, opciones, pesos)
        if valores:
            return random.choices(opciones, weights=valores, k=1)[0]
        return random.choice(opciones)

    return _elegir_con_sesgo(persona, opciones)


def _elegir_con_sesgo(persona: Persona, opciones: list) -> str:
    """
    Sin pesos definidos, la personalidad sesga la elección:
    optimista hacia las últimas opciones, pesimista hacia las
    primeras, el resto hacia el centro.
    """
    n = len(opciones)
    if n == 1:
        return opciones[0]

    mitad = n // 2
    if persona.personalidad == "optimista":
        pesos = [1] * mitad + [3] * (n - mitad)
    elif persona.personalidad == "pesimista":
        pesos = [3] * mitad + [1] * (n - mitad)
    else:
        pesos = [2] * n
        if n > 2:
            pesos[n // 2] += 1

    return random.choices(opciones, weights=pesos, k=1)[0]


# -------------------------------------------------------------
# Tipo: escala numérica
# -------------------------------------------------------------
def _responder_escala(persona: Persona, pregunta: dict) -> str:
    """
    Devuelve un valor de la escala según el perfil. Si la pregunta
    define 'rango_forzado' [min, max], restringe los valores
    posibles a ese rango (la personalidad sigue influyendo dentro).
    """
    minimo = pregunta.get("min", 1)
    maximo = pregunta.get("max", 5)

    rango_forzado = pregunta.get("rango_forzado")
    if rango_forzado:
        minimo, maximo = rango_forzado

    rango = list(range(minimo, maximo + 1))
    n = len(rango)
    if n == 1:
        return str(rango[0])

    if persona.personalidad == "optimista":
        pesos = [max(1, i * 3) for i in range(1, n + 1)]
    elif persona.personalidad == "pesimista":
        pesos = [max(1, (n - i + 1) * 3) for i in range(1, n + 1)]
    elif persona.personalidad == "practico":
        centro = n / 2
        pesos = [max(1, int(10 - abs(i - centro) * 3)) for i in range(1, n + 1)]
    elif persona.personalidad == "emocional":
        pesos = [3] * n
        pesos[0] += 2
        pesos[-1] += 2
    else:
        pesos = [2] * n

    if persona.economia == "alto" and n >= 3:
        pesos[-1] += 2
        pesos[-2] += 1
    elif persona.economia == "bajo" and n >= 3:
        pesos[0] += 2
        pesos[1] += 1

    return str(random.choices(rango, weights=pesos, k=1)[0])


# -------------------------------------------------------------
# Tipo: checkboxes (selección múltiple)
# -------------------------------------------------------------
def _responder_checkboxes(persona: Persona, pregunta: dict) -> str:
    """
    Selecciona una o varias opciones con probabilidad independiente
    por opción (según educación). 'Ninguna' es excluyente: solo se
    devuelve si no se marcó nada más. Siempre devuelve al menos una
    opción, de modo que la pregunta obligatoria nunca queda vacía.
    """
    opciones = pregunta.get("opciones", [])
    if not opciones:
        return "Ninguna"

    pesos = pregunta.get("pesos_seleccion", {})
    clave = f"educacion_{persona.educacion}"
    probabilidades = pesos.get(clave, [0.35] * len(opciones))

    seleccionadas = [
        opcion
        for i, opcion in enumerate(opciones)
        if opcion != "Ninguna"
        and random.random() < (probabilidades[i] if i < len(probabilidades) else 0.35)
    ]

    if seleccionadas:
        return ", ".join(seleccionadas)

    # No se marcó nada: elegir entre 'Ninguna' o forzar una opción.
    prob_ninguna = probabilidades[-1] if probabilidades else 0.3
    if "Ninguna" in opciones and random.random() < prob_ninguna:
        return "Ninguna"

    reales = [o for o in opciones if o != "Ninguna"]
    pesos_reales = [
        probabilidades[i] for i, o in enumerate(opciones) if o != "Ninguna"
    ]
    return random.choices(reales, weights=pesos_reales, k=1)[0]


# -------------------------------------------------------------
# Encuesta completa
# -------------------------------------------------------------
def responder_encuesta(persona: Persona, preguntas: list[dict]) -> dict:
    """
    Devuelve un diccionario con el perfil de la persona y su
    respuesta a cada pregunta, bajo claves P01, P02, ...
    """
    respuestas = {
        "nombre": persona.nombre,
        "edad": persona.edad,
        "genero": persona.genero,
        "educacion": persona.educacion,
        "economia": persona.economia,
        "personalidad": persona.personalidad,
        "region": persona.region,
    }
    for pregunta in preguntas:
        clave = f"P{pregunta['id']:02d}"
        respuestas[clave] = responder_pregunta(persona, pregunta)
    return respuestas


# -------------------------------------------------------------
# Prueba directa: python3 -m src.response_engine
# -------------------------------------------------------------
if __name__ == "__main__":
    from rich.console import Console
    from rich.table import Table

    from src.config import ENCUESTA
    from src.persona_engine import generar_persona

    console = Console()
    preguntas = ENCUESTA["preguntas"]

    console.print("\n[bold cyan]⚗️  ANTARES FORMS — Motor de Respuestas[/bold cyan]")
    console.print("[dim]Simulando 5 personas sobre la encuesta real...[/dim]\n")

    for i in range(5):
        persona = generar_persona()
        respuestas = responder_encuesta(persona, preguntas)

        tabla = Table(
            title=f"#{i + 1}: {persona.nombre} | {persona.educacion} | {persona.personalidad}",
            header_style="bold yellow",
        )
        tabla.add_column("Pregunta", style="dim", width=42)
        tabla.add_column("Respuesta", style="green", width=34)
        for pregunta in preguntas:
            clave = f"P{pregunta['id']:02d}"
            tabla.add_row(pregunta["texto"][:40] + "…", respuestas[clave])
        console.print(tabla)
        console.print()

    console.print("[bold green]✅ Motor de Respuestas funcionando correctamente.[/bold green]\n")
