# =============================================================
# ANTARES FORMS — Tests de la lógica de simulación
# Archivo: tests/test_logica.py
# Ejecutar:  python3 -m pytest -v
#            python3 -m pytest tests/test_logica.py
#
# Estos tests NO abren el navegador: validan la generación de
# personas y respuestas, que es la parte determinante de la
# calidad académica del proyecto. La capa Playwright se prueba
# manualmente con `python3 main.py` contra el formulario real.
# =============================================================

import re

import pytest

from src.config import ENCUESTA
from src.form_filler import normalizar_url
from src.persona_engine import (
    PERSONALIDADES,
    Persona,
    generar_grupo,
    generar_persona,
)
from src.response_engine import responder_encuesta, responder_pregunta

PREGUNTAS = ENCUESTA["preguntas"]
N = 2000  # tamaño de muestra para tests estadísticos


# -------------------------------------------------------------
# Motor de personas
# -------------------------------------------------------------
def test_persona_tiene_campos_validos():
    p = generar_persona()
    assert isinstance(p, Persona)
    assert 18 <= p.edad <= 70
    assert p.genero in ("masculino", "femenino")
    assert p.educacion in ("basico", "medio", "universitario", "posgrado")
    assert p.economia in ("bajo", "medio", "alto")
    assert p.personalidad in PERSONALIDADES
    assert p.nombre.strip()


def test_grupo_genera_cantidad_exacta():
    assert len(generar_grupo(50)) == 50


def test_coherencia_edad_grupo():
    for p in generar_grupo(N):
        if p.edad <= 25:
            assert p.grupo_edad == "joven"
        elif p.edad <= 40:
            assert p.grupo_edad == "adulto"
        elif p.edad <= 55:
            assert p.grupo_edad == "maduro"
        else:
            assert p.grupo_edad == "mayor"


# -------------------------------------------------------------
# Motor de respuestas
# -------------------------------------------------------------
def test_ninguna_respuesta_vacia():
    """Crítico: una respuesta vacía haría fallar el envío (campo obligatorio)."""
    for _ in range(N):
        p = generar_persona()
        r = responder_encuesta(p, PREGUNTAS)
        for q in PREGUNTAS:
            assert r[f"P{q['id']:02d}"].strip(), f"P{q['id']:02d} salió vacía"


def test_escala_dentro_de_rango():
    for _ in range(N):
        p = generar_persona()
        r = responder_encuesta(p, PREGUNTAS)
        for q in PREGUNTAS:
            if q["tipo"] == "escala":
                lo, hi = q.get("rango_forzado", (q["min"], q["max"]))
                assert lo <= int(r[f"P{q['id']:02d}"]) <= hi


def test_rango_forzado_p9_p10():
    """P9 y P10 nunca deben bajar de 3 (rango_forzado [3,5])."""
    for _ in range(N):
        p = generar_persona()
        r = responder_encuesta(p, PREGUNTAS)
        assert int(r["P09"]) >= 3
        assert int(r["P10"]) >= 3


def test_opcion_multiple_es_valida():
    for _ in range(N):
        p = generar_persona()
        for q in PREGUNTAS:
            if q["tipo"] == "opcion_multiple":
                assert responder_pregunta(p, q) in q["opciones"]


def test_checkboxes_opciones_validas():
    """Cada elemento devuelto debe ser una opción real del config."""
    pregunta_cb = next(q for q in PREGUNTAS if q["tipo"] == "checkboxes")
    validas = set(pregunta_cb["opciones"])
    for _ in range(N):
        p = generar_persona()
        resp = responder_pregunta(p, pregunta_cb)
        for item in resp.split(", "):
            assert item in validas


def test_ninguna_es_excluyente():
    """Si la respuesta es 'Ninguna', no puede venir con otra opción."""
    pregunta_cb = next(q for q in PREGUNTAS if q["tipo"] == "checkboxes")
    for _ in range(N):
        p = generar_persona()
        resp = responder_pregunta(p, pregunta_cb)
        if "Ninguna" in resp:
            assert resp == "Ninguna"


def test_hay_variacion_entre_personas():
    """100 personas no deben dar 100 respuestas idénticas (objetivo del proyecto)."""
    firmas = set()
    for _ in range(100):
        p = generar_persona()
        r = responder_encuesta(p, PREGUNTAS)
        firmas.add(tuple(r[f"P{q['id']:02d}"] for q in PREGUNTAS))
    assert len(firmas) > 50, "Variación insuficiente entre respuestas"


# -------------------------------------------------------------
# Normalización de URL (form_filler)
# -------------------------------------------------------------
@pytest.mark.parametrize(
    "entrada,esperada",
    [
        ("https://docs.google.com/forms/d/e/ABC/viewform",
         "https://docs.google.com/forms/d/e/ABC/viewform"),
        ("https://docs.google.com/forms/d/e/ABC/edit",
         "https://docs.google.com/forms/d/e/ABC/viewform"),
        ("https://docs.google.com/forms/d/e/ABC/viewform?usp=sharing&ouid=123",
         "https://docs.google.com/forms/d/e/ABC/viewform"),
        ("https://docs.google.com/forms/d/e/ABC/",
         "https://docs.google.com/forms/d/e/ABC/viewform"),
    ],
)
def test_normalizar_url(entrada, esperada):
    assert normalizar_url(entrada) == esperada


# -------------------------------------------------------------
# Integridad del config
# -------------------------------------------------------------
def test_ids_consecutivos_y_unicos():
    ids = [q["id"] for q in PREGUNTAS]
    assert ids == list(range(1, len(ids) + 1))


def test_pesos_coinciden_con_opciones():
    """Cada vector de pesos debe tener tantos valores como opciones."""
    for q in PREGUNTAS:
        opciones = q.get("opciones", [])
        for clave in ("pesos", "pesos_seleccion"):
            for atributo, vector in q.get(clave, {}).items():
                assert len(vector) == len(opciones), (
                    f"P{q['id']} {clave}[{atributo}]: "
                    f"{len(vector)} pesos vs {len(opciones)} opciones"
                )
