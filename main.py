# =============================================================
# ANTARES FORMS — Orquestador Principal (auditado)
# Archivo: main.py
# Uso: python3 main.py
#
# Mejoras de auditoría:
#   - Usa enviar_con_reintentos (3 intentos) para recuperar los
#     fallos transitorios que antes dejaban ~10/100 sin enviar.
#   - Guardado incremental: cada respuesta se persiste en el acto,
#     de modo que una interrupción (Ctrl+C, corte) no pierde el
#     progreso ya logrado.
#   - Captura de KeyboardInterrupt para cierre limpio del browser.
#   - Validación de entrada reforzada y un único punto de logging.
# =============================================================

from __future__ import annotations

import csv
import json
import random
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.prompt import IntPrompt, Prompt

from src.config import ENCUESTA
from src.form_filler import (
    CHROMIUM_PATH,
    LAUNCH_ARGS,
    VELOCIDADES,
    enviar_con_reintentos,
)
from src.persona_engine import generar_persona
from src.response_engine import responder_encuesta

console = Console()

MIN_ENVIOS = 1
MAX_ENVIOS = 500


# -------------------------------------------------------------
# Configuración interactiva
# -------------------------------------------------------------
def pedir_configuracion() -> dict:
    """Solicita y valida los parámetros de la simulación."""
    console.print("\n[yellow]⚙️  Configuración[/yellow]\n")

    url = Prompt.ask("[cyan]  URL del Google Form[/cyan]").strip()
    if "docs.google.com/forms" not in url:
        console.print("[red]❌ URL inválida. Debe ser un Google Form.[/red]")
        sys.exit(1)

    cantidad = IntPrompt.ask(
        "[cyan]  ¿Cuántas veces responder el formulario?[/cyan]", default=10
    )
    if not MIN_ENVIOS <= cantidad <= MAX_ENVIOS:
        console.print(f"[red]❌ Debe ser entre {MIN_ENVIOS} y {MAX_ENVIOS}.[/red]")
        sys.exit(1)

    nombre_vel = Prompt.ask(
        "[cyan]  Velocidad[/cyan]",
        choices=list(VELOCIDADES.keys()),
        default="normal",
    )

    ver = Prompt.ask(
        "[cyan]  ¿Ver el navegador? (s/n)[/cyan]", default="n"
    ).lower().startswith("s")

    debug = Prompt.ask(
        "[cyan]  ¿Modo diagnóstico? (s/n)[/cyan]", default="n"
    ).lower().startswith("s")

    return {
        "url": url,
        "cantidad": cantidad,
        "nombre_vel": nombre_vel,
        "perfil": VELOCIDADES[nombre_vel],
        "headless": not ver,
        "debug": debug,
    }


# -------------------------------------------------------------
# Persistencia incremental
# -------------------------------------------------------------
def construir_fila(agente: int, persona, respuestas: dict, exito: bool) -> dict:
    """Aplana una respuesta en una fila lista para CSV/JSON."""
    fila = {
        "agente": agente,
        "nombre": persona.nombre,
        "edad": persona.edad,
        "genero": persona.genero,
        "educacion": persona.educacion,
        "economia": persona.economia,
        "personalidad": persona.personalidad,
        "region": persona.region,
        "exito": exito,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    for pregunta in ENCUESTA["preguntas"]:
        clave = f"P{pregunta['id']:02d}"
        fila[f"{clave}_respuesta"] = respuestas.get(clave, "")
    return fila


def guardar(filas: list[dict], ruta_json: Path, ruta_csv: Path) -> None:
    """Reescribe los archivos de log con todas las filas acumuladas."""
    ruta_json.write_text(
        json.dumps(filas, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if filas:
        with ruta_csv.open("w", newline="", encoding="utf-8") as fichero:
            escritor = csv.DictWriter(fichero, fieldnames=filas[0].keys())
            escritor.writeheader()
            escritor.writerows(filas)


# -------------------------------------------------------------
# Bucle principal
# -------------------------------------------------------------
def ejecutar(cfg: dict) -> None:
    preguntas = ENCUESTA["preguntas"]
    perfil = cfg["perfil"]

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    sello = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta_json = log_dir / f"resultados_{sello}.json"
    ruta_csv = log_dir / f"resultados_{sello}.csv"

    console.print("\n[green]✅ Todo listo[/green]")
    console.print(f"[dim]  • Envíos:    {cfg['cantidad']}[/dim]")
    console.print(f"[dim]  • Velocidad: {cfg['nombre_vel']}[/dim]")
    console.print(f"[dim]  • Navegador: {'Oculto' if cfg['headless'] else 'Visible'}[/dim]")
    console.print(f"[dim]  • Log CSV:   {ruta_csv}[/dim]\n")

    if not Prompt.ask(
        "[yellow]  ¿Iniciar simulación? (s/n)[/yellow]", default="s"
    ).lower().startswith("s"):
        sys.exit(0)

    console.print()
    filas: list[dict] = []
    exitosos = 0

    with sync_playwright() as play:
        browser = play.chromium.launch(
            executable_path=CHROMIUM_PATH,
            headless=cfg["headless"],
            slow_mo=perfil.slow_mo,
            args=LAUNCH_ARGS,
        )
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[cyan]{task.completed}/{task.total}[/cyan]"),
                TimeRemainingColumn(),
                console=console,
            ) as progreso:
                tarea = progreso.add_task("[cyan]Simulando…[/cyan]", total=cfg["cantidad"])

                for agente in range(1, cfg["cantidad"] + 1):
                    progreso.update(tarea, description=f"[cyan]Agente #{agente:03d}[/cyan]")

                    persona = generar_persona()
                    respuestas = responder_encuesta(persona, preguntas)
                    exito = enviar_con_reintentos(
                        browser, cfg["url"], respuestas, preguntas, perfil,
                        debug=cfg["debug"],
                    )

                    filas.append(construir_fila(agente, persona, respuestas, exito))
                    guardar(filas, ruta_json, ruta_csv)  # incremental

                    if exito:
                        exitosos += 1
                        progreso.print(
                            f"  [green]✅ #{agente:03d}[/green] {persona.nombre} | "
                            f"{persona.educacion} | {persona.personalidad}"
                        )
                    else:
                        progreso.print(
                            f"  [red]❌ #{agente:03d}[/red] {persona.nombre} — Falló"
                        )

                    progreso.advance(tarea)

                    if agente < cfg["cantidad"]:
                        time.sleep(random.uniform(perfil.pausa_entre_min,
                                                  perfil.pausa_entre_max))
        except KeyboardInterrupt:
            console.print("\n[yellow]⚠️ Interrumpido por el usuario. "
                          "Guardando lo avanzado…[/yellow]")
        finally:
            browser.close()

    guardar(filas, ruta_json, ruta_csv)
    _resumen(exitosos, len(filas), ruta_csv, ruta_json)


def _resumen(exitosos: int, total: int, ruta_csv: Path, ruta_json: Path) -> None:
    fallidos = total - exitosos
    console.print()
    console.print(
        Panel.fit(
            f"[bold green]🏆 SIMULACIÓN COMPLETADA[/bold green]\n\n"
            f"[green]✅ Exitosos:[/green]  {exitosos} / {total}\n"
            f"[red]❌ Fallidos:[/red]   {fallidos} / {total}\n\n"
            f"[dim]📊 {ruta_csv}[/dim]\n"
            f"[dim]📄 {ruta_json}[/dim]",
            border_style="green",
        )
    )


def main() -> None:
    console.print(
        Panel.fit(
            "[bold cyan]⚗️  ANTARES FORMS[/bold cyan]\n"
            "[dim]Simulador de respuestas humanas — Proyecto universitario[/dim]",
            border_style="cyan",
        )
    )
    ejecutar(pedir_configuracion())


if __name__ == "__main__":
    main()
