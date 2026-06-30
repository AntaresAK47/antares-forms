# =============================================================
# ANTARES FORMS — Motor de Automatización (v5, auditado)
# Archivo: src/form_filler.py
#
# Cambios clave respecto a la v4:
#   - Reintentos automáticos por agente (configurable).
#   - Espera explícita de navegación con expect_navigation, en
#     lugar de un sleep fijo + lectura de URL (elimina la causa
#     principal de los fallos 10/100: la página aún no había
#     terminado de procesar el envío cuando se leía la URL).
#   - Checkboxes seleccionados SIEMPRE por aria-label (la única
#     vía fiable en Google Forms; inner_text viene vacío). Las
#     estrategias 3 y 4 de la v4 eran código muerto: nunca se
#     alcanzaban porque la 1 siempre acertaba. Eliminadas.
#   - Detección de "pregunta obligatoria sin responder": si tras
#     pulsar Enviar la URL NO cambia y el formulario muestra un
#     aviso de campo requerido, se reporta como fallo real (antes
#     se confundía con un timeout).
#   - El locator de cada radiogroup se vuelve a calcular en el
#     momento de usarlo (evita ElementHandle obsoletos tras el
#     scroll, otra fuente de fallos intermitentes).
#   - Type hints completos y constantes nombradas.
# =============================================================

from __future__ import annotations

import random
import time
from dataclasses import dataclass

from playwright.sync_api import Browser, Page, TimeoutError as PlaywrightTimeout

# Ruta del Chromium del sistema (snap en Ubuntu 24.04+).
CHROMIUM_PATH = "/usr/bin/chromium-browser"

# Argumentos de lanzamiento necesarios para el Chromium snap.
LAUNCH_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
]


# -------------------------------------------------------------
# Perfiles de velocidad
# -------------------------------------------------------------
@dataclass(frozen=True)
class PerfilVelocidad:
    """Parámetros de temporización para un modo de velocidad."""
    slow_mo: int          # ms de ralentización global de Playwright
    pausa_min: float      # pausa mínima entre acciones (s)
    pausa_max: float      # pausa máxima entre acciones (s)
    espera_navegacion: int  # timeout de espera de navegación tras enviar (ms)
    pausa_entre_min: float  # pausa mínima entre agentes (s)
    pausa_entre_max: float  # pausa máxima entre agentes (s)


VELOCIDADES: dict[str, PerfilVelocidad] = {
    "rapida": PerfilVelocidad(0,  0.05, 0.15, 12000, 0.3, 0.8),
    "normal": PerfilVelocidad(20, 0.20, 0.40, 12000, 0.8, 1.5),
    "humana": PerfilVelocidad(60, 0.40, 0.90, 15000, 2.0, 4.0),
}

# Reintentos por agente cuando el envío no se confirma.
MAX_INTENTOS = 3


# -------------------------------------------------------------
# Utilidades internas
# -------------------------------------------------------------
def _pausa(perfil: PerfilVelocidad) -> None:
    """Pausa breve y aleatoria para imitar comportamiento humano."""
    time.sleep(random.uniform(perfil.pausa_min, perfil.pausa_max))


def normalizar_url(url: str) -> str:
    """
    Devuelve la URL pública de respuesta (/viewform) a partir de
    cualquier variante: /edit, con parámetros, o ya en /viewform.
    """
    base = url.split("?", 1)[0].rstrip("/")
    if base.endswith("/edit"):
        base = base[: -len("/edit")] + "/viewform"
    elif not base.endswith("/viewform"):
        base = base + "/viewform"
    return base


def _forzar_render(page: Page) -> None:
    """
    Hace scroll al final y vuelve arriba para forzar a Google Forms
    a renderizar todas las preguntas (carga perezosa).
    """
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(0.8)
    page.evaluate("window.scrollTo(0, 0)")
    time.sleep(0.4)


# -------------------------------------------------------------
# Selección de respuestas
# -------------------------------------------------------------
def _click_radio_por_indice(
    page: Page, indice_grupo: int, indice_opcion: int, perfil: PerfilVelocidad
) -> bool:
    """
    Marca, dentro del radiogroup 'indice_grupo', la opción
    'indice_opcion' (ambos 0-based). Recalcula el locator en el
    momento para evitar handles obsoletos. Sirve igual para
    opción múltiple y para escala lineal.
    """
    try:
        grupo = page.locator('div[role="radiogroup"]').nth(indice_grupo)
        opcion = grupo.locator('div[role="radio"]').nth(indice_opcion)
        opcion.scroll_into_view_if_needed(timeout=4000)
        opcion.click(timeout=4000)
        _pausa(perfil)
        return True
    except Exception:
        return False


def _click_checkboxes(
    page: Page, respuesta: str, perfil: PerfilVelocidad, debug: bool = False
) -> bool:
    """
    Marca las casillas indicadas usando el aria-label exacto, que
    es el único atributo fiable en Google Forms (inner_text viene
    vacío). 'respuesta' es una cadena separada por comas, o
    'Ninguna'. Devuelve True si marcó al menos una (o si era
    'Ninguna', que no requiere acción aquí salvo marcarla).
    """
    texto = respuesta.strip()
    if not texto:
        return False

    seleccionadas = [t.strip() for t in texto.split(",") if t.strip()]
    marcadas = 0

    for etiqueta in seleccionadas:
        try:
            casilla = page.locator(
                f'div[role="checkbox"][aria-label="{etiqueta}"]'
            )
            if casilla.count() == 0:
                if debug:
                    print(f"      ❌ Sin aria-label: '{etiqueta}'")
                continue
            casilla.first.scroll_into_view_if_needed(timeout=4000)
            casilla.first.click(timeout=4000)
            marcadas += 1
            _pausa(perfil)
            if debug:
                print(f"      ✅ '{etiqueta}'")
        except Exception:
            if debug:
                print(f"      ⚠️ No se pudo marcar: '{etiqueta}'")

    return marcadas > 0


# -------------------------------------------------------------
# Envío y confirmación
# -------------------------------------------------------------
def _enviar_y_confirmar(page: Page, perfil: PerfilVelocidad, debug: bool) -> bool:
    """
    Pulsa el botón Enviar y espera la navegación a /formResponse.
    Usa expect_navigation para sincronizar de forma fiable, en
    lugar de un sleep fijo. Devuelve True solo si Google confirma.
    """
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(0.5)

    selectores = [
        'div[role="button"]:has-text("Enviar")',
        'div[role="button"]:has-text("Submit")',
        'div[role="button"][aria-label="Enviar"]',
        'div[role="button"][aria-label="Submit"]',
    ]

    try:
        with page.expect_navigation(
            url="**/formResponse**", timeout=perfil.espera_navegacion
        ):
            pulsado = False
            for selector in selectores:
                try:
                    page.locator(selector).last.click(timeout=4000)
                    pulsado = True
                    if debug:
                        print(f"    🖱️  Enviar via: {selector}")
                    break
                except Exception:
                    continue
            if not pulsado:
                raise PlaywrightTimeout("No se encontró el botón Enviar")
        if debug:
            print("    ✅ Navegó a /formResponse — envío confirmado")
        return True

    except PlaywrightTimeout:
        # No hubo navegación: o falló el botón, o quedó una pregunta
        # obligatoria sin marcar. Distinguimos ambos casos.
        if _hay_pregunta_requerida(page):
            if debug:
                print("    ❌ Pregunta obligatoria sin responder")
        elif debug:
            print("    ❌ Sin navegación a /formResponse (timeout)")
        return False


def _hay_pregunta_requerida(page: Page) -> bool:
    """
    Detecta si Google Forms muestra el aviso de campo obligatorio
    sin responder. Útil para diferenciar un fallo de validación
    de un simple timeout de red.
    """
    avisos = [
        "es una pregunta obligatoria",
        "esta pregunta es obligatoria",
        "this is a required question",
    ]
    try:
        contenido = page.content().lower()
        return any(aviso in contenido for aviso in avisos)
    except Exception:
        return False


# -------------------------------------------------------------
# Función pública: rellenar y enviar un formulario
# -------------------------------------------------------------
def enviar_respuesta(
    browser: Browser,
    url: str,
    respuestas: dict,
    preguntas: list[dict],
    perfil: PerfilVelocidad,
    debug: bool = False,
) -> bool:
    """
    Rellena y envía el formulario UNA vez (sin reintentos).

    Devuelve True solo si Google Forms confirma el envío
    (navegación a /formResponse).
    """
    page = browser.new_page()
    try:
        page.goto(normalizar_url(url), wait_until="domcontentloaded", timeout=30000)
        _forzar_render(page)
        page.wait_for_selector('div[role="radio"]', timeout=10000)

        total_grupos = page.locator('div[role="radiogroup"]').count()
        if debug:
            print(f"    🔍 Radiogroups detectados: {total_grupos}")

        indice_grupo = 0
        for pregunta in preguntas:
            tipo = pregunta["tipo"]
            clave = f"P{pregunta['id']:02d}"
            respuesta = respuestas.get(clave, "")

            if tipo == "opcion_multiple":
                opciones = pregunta.get("opciones", [])
                idx = opciones.index(respuesta) if respuesta in opciones else 0
                ok = _click_radio_por_indice(page, indice_grupo, idx, perfil)
                if debug:
                    print(f"    {clave} radio[{indice_grupo}] '{respuesta}': "
                          f"{'✅' if ok else '❌'}")
                indice_grupo += 1

            elif tipo == "escala":
                idx = int(respuesta) - 1  # valor 1..5 -> índice 0..4
                ok = _click_radio_por_indice(page, indice_grupo, idx, perfil)
                if debug:
                    print(f"    {clave} escala[{indice_grupo}] val={respuesta}: "
                          f"{'✅' if ok else '❌'}")
                indice_grupo += 1

            elif tipo == "checkboxes":
                if debug:
                    print(f"    {clave} checkboxes '{respuesta}':")
                _click_checkboxes(page, respuesta, perfil, debug=debug)

        return _enviar_y_confirmar(page, perfil, debug)

    except Exception as exc:
        if debug:
            print(f"    ❌ Excepción al rellenar: {exc}")
        return False
    finally:
        page.close()


def enviar_con_reintentos(
    browser: Browser,
    url: str,
    respuestas: dict,
    preguntas: list[dict],
    perfil: PerfilVelocidad,
    max_intentos: int = MAX_INTENTOS,
    debug: bool = False,
) -> bool:
    """
    Envuelve enviar_respuesta con reintentos. La mayoría de los
    fallos 10/100 son transitorios (red, render lento); un
    segundo intento suele resolverlos.
    """
    for intento in range(1, max_intentos + 1):
        if debug and intento > 1:
            print(f"    🔁 Reintento {intento}/{max_intentos}")
        if enviar_respuesta(browser, url, respuestas, preguntas, perfil, debug):
            return True
        time.sleep(random.uniform(1.0, 2.0))
    return False
