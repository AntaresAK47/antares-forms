# ⚗️ Antares Forms

Simulador de respuestas humanas para Google Forms. Genera *personas
virtuales* con perfiles coherentes (edad, educación, economía,
personalidad) y responde un formulario N veces de forma variada pero
lógica, automatizando el navegador con Playwright.

Proyecto académico: demuestra cómo un bot puede simular respuestas
humanas plausibles en una encuesta sobre phishing y ciberseguridad.

> **Uso responsable.** Está pensado para ejecutarse contra un
> formulario propio, con fines de demostración académica. No lo use
> para manipular encuestas de terceros.

---

## Requisitos

- Ubuntu 24.04+ (probado en 26.04 / "resolute").
- Python 3.10 o superior.
- Chromium del sistema en `/usr/bin/chromium-browser`
  (`sudo apt install chromium-browser`).
- [uv](https://docs.astral.sh/uv/) (recomendado) o `pip` + `venv`.

> Playwright **no** descarga su Chromium interno: usa el del sistema
> mediante `executable_path`, porque el binario interno aún no da
> soporte a esta versión de Ubuntu.

---

## Instalación

### Opción A — uv (recomendada)

[uv](https://docs.astral.sh/uv/) gestiona el entorno virtual y las
dependencias con un archivo de bloqueo (`uv.lock`) que garantiza la
misma instalación exacta en cualquier máquina.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
cd "ruta/del/proyecto"
uv sync
```

### Opción B — venv clásico

Sin dependencias adicionales, con las herramientas estándar de Python.

```bash
cd "ruta/del/proyecto"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Uso

### Con uv

```bash
uv run python main.py
```

### Con venv clásico

```bash
source .venv/bin/activate      # al inicio de cada sesión
python3 main.py
```

El programa pregunta de forma interactiva:

| Parámetro    | Descripción                                            |
|--------------|----------------------------------------------------------|
| URL          | Enlace público del formulario (`/viewform`).            |
| Cantidad     | Cuántas veces responder (1–500).                         |
| Velocidad    | `rapida`, `normal` o `humana`.                           |
| Navegador    | Visible (`s`) u oculto/headless (`n`).                   |
| Diagnóstico  | Muestra el detalle de cada paso (`s`/`n`).                |

Los resultados se guardan en `logs/` como CSV y JSON, de forma
incremental (no se pierde el avance si se interrumpe).

---

## Estructura
.
├── main.py                 # Orquestador: pregunta, ejecuta y registra
├── pyproject.toml          # Metadatos y dependencias (estándar PEP 621)
├── uv.lock                 # Versiones exactas bloqueadas (uv)
├── requirements.txt        # Dependencias para instalación con pip clásico
├── README.md
├── AUDITORIA.md
├── src/
│   ├── config.py           # Las 10 preguntas reales del formulario
│   ├── persona_engine.py   # Genera personas virtuales coherentes
│   ├── response_engine.py  # Genera respuestas lógicas por perfil
│   └── form_filler.py      # Automatiza el navegador (Playwright)
└── tests/
└── test_logica.py      # Tests de la lógica (sin navegador)

---

## Cómo funciona la "IA sencilla"

No hay un modelo entrenado: hay **probabilidades ponderadas** que
imitan correlaciones reales. Cada persona tiene un perfil, y ese
perfil sesga sus respuestas:

- Economía alta → tiende a optimista; baja → tiende a pesimista.
- Mayor educación → más probabilidad de verificar URLs y reconocer
  señales de phishing.
- Personalidad → sesga las escalas hacia valores altos, bajos o
  centrales.

Así, 100 personas producen 100 conjuntos de respuestas distintos
pero plausibles.

---

## Tipos de pregunta soportados

| Tipo              | Cómo se rellena en el formulario                  |
|-------------------|-------------------------------------------------|
| `opcion_multiple` | Radio por **índice** de la opción.               |
| `escala`          | Radio por índice (valor 1–5 → posición 0–4).     |
| `checkboxes`      | Casillas por **`aria-label`** exacto.            |

`escala` admite `rango_forzado: [min, max]` para acotar la respuesta
(p. ej. P9 y P10 nunca bajan de 3).

---

## Tests

### Con uv

```bash
uv run pytest -v
```

### Con venv clásico

```bash
pip install pytest
python3 -m pytest -v
```

Cubren generación de personas, validez y variación de respuestas,
`rango_forzado`, normalización de URL e integridad del `config.py`.
La capa de navegador se valida manualmente ejecutando `main.py`.
