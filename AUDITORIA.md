# 🔍 Informe de Auditoría — Antares Forms

Auditoría de código, depuración, eliminación de código muerto,
optimización y tests. Documento de referencia de los cambios.

---

## 1. Resumen ejecutivo

El proyecto funcionaba, pero con tres clases de problema:

1. **Fallos intermitentes en el envío (~10/100).** Causa raíz: la
   confirmación del envío se basaba en un `sleep` fijo seguido de
   una lectura de URL. Cuando el procesamiento de Google Forms
   tardaba más que ese sleep, el bot leía la URL **antes** de que
   cambiara y lo marcaba como fallo, aunque a veces sí se enviaba —
   y otras no se enviaba por una pregunta obligatoria sin marcar,
   sin que el código lo distinguiera.
2. **Código muerto** (~250 líneas): un banco de ~200 frases y dos
   tipos de pregunta (`si_no`, `texto_abierto`) que el formulario
   real no usa; y dos estrategias de checkbox que nunca se
   alcanzaban.
3. **Archivos de soporte vacíos o ausentes**: `requirements.txt` y
   `logger.py` vacíos, sin `.gitignore`, sin tests.

Tras la auditoría: **0 respuestas vacías** en 3000 simulaciones,
**16 tests** en verde, y un mecanismo de **reintentos + espera de
navegación real** que ataca directamente los fallos 10/100.

---

## 2. Causa raíz de los fallos 10/100 (el punto importante)

### Lo que hacía la versión anterior (`_enviar` + `_fue_confirmado`)

```python
page.locator(selector).last.click(...)      # pulsa Enviar
page.wait_for_url(lambda u: u != url_antes, timeout=8000)
...
page.wait_for_timeout(config["post_envio"]) # sleep fijo 2-3 s
if "formresponse" in page.url: ...           # lee la URL DESPUÉS
```

Dos defectos:

- **Carrera (race condition).** Entre el click y la comprobación
  había un sleep fijo. Si la red o el render de la página de
  confirmación tardaban más, la URL todavía no era `/formResponse`
  y el envío se daba por fallido aunque estuviera en curso.
- **No se distinguía "timeout" de "campo obligatorio sin marcar".**
  Si un checkbox no se marcaba (p. ej. por un handle obsoleto tras
  el scroll), el formulario rechazaba el envío y la URL no cambiaba
  — exactamente el mismo síntoma que un timeout de red. El código
  no sabía cuál de los dos era.

### Lo que hace la versión auditada (`_enviar_y_confirmar`)

```python
with page.expect_navigation(url="**/formResponse**",
                            timeout=perfil.espera_navegacion):
    page.locator(selector).last.click(...)   # pulsa DENTRO del contexto
# Si entra aquí, la navegación a /formResponse YA ocurrió.
```

- `expect_navigation` **sincroniza con el evento real** de
  navegación, en vez de adivinar con un sleep. Espera hasta 12–15 s
  a que la URL pase a `/formResponse`; si ocurre, es éxito seguro.
- Si **no** ocurre, se inspecciona la página para ver si hay un
  aviso de pregunta obligatoria (`_hay_pregunta_requerida`) y se
  distingue del timeout puro en el log de diagnóstico.

### Refuerzos adicionales contra la intermitencia

- **Reintentos por agente** (`enviar_con_reintentos`, 3 intentos).
  La mayoría de los fallos restantes son transitorios; un segundo
  intento los recupera.
- **Locators recalculados al usarse.** Antes se guardaba la lista de
  radiogroups y se reutilizaban los handles tras hacer scroll, lo
  que podía dejar referencias obsoletas (`ElementHandle` detached).
  Ahora cada click recalcula `nth(i)` en el momento.

---

## 3. Código muerto eliminado

| Elemento                                   | Líneas aprox. | Motivo                                              |
|--------------------------------------------|---------------|-----------------------------------------------------|
| `_BANCO_FRASES` (5 temas × 5 personalidades) | ~200          | Ningún tipo `texto_abierto` en el formulario real.  |
| `_responder_texto_abierto`                 | ~18           | Sin uso.                                            |
| `_responder_si_no`                         | ~40           | El formulario no tiene preguntas Sí/No.             |
| Estrategias 3 y 4 de checkbox (`inner_text`, JS) | ~25      | Inalcanzables: el `aria-label` (estrategia 1) siempre acierta. El diagnóstico confirmó que `inner_text` viene vacío en Google Forms. |
| `preguntas_demo` embebidas en `__main__`   | ~35           | Reemplazadas por el `config.py` real en la demo.    |

`response_engine.py` pasó de **595 a ~250 líneas** sin perder
ninguna funcionalidad usada.

---

## 4. Mejoras de arquitectura y buenas prácticas

- **`VELOCIDADES` como `dataclass(frozen=True)`** (`PerfilVelocidad`)
  en lugar de diccionarios sueltos: acceso por atributo, inmutable y
  autocompletado en el editor.
- **`LAUNCH_ARGS` centralizado**: los argumentos de Chromium estaban
  duplicados entre `main.py` y `form_filler.py`. Ahora viven en un
  solo sitio.
- **Guardado incremental de logs**: cada respuesta se persiste al
  instante. Una interrupción a mitad de 100 envíos ya no pierde lo
  avanzado.
- **`KeyboardInterrupt` capturado**: Ctrl+C cierra el navegador de
  forma limpia y guarda lo hecho.
- **`pedir_configuracion` separada** del bucle de ejecución:
  `main.py` queda legible y testeable por partes.
- **Helper `_pesos_por_atributo`**: las tres ramas casi idénticas de
  `_aplicar_pesos_personalizados` se unificaron en una.
- **`from __future__ import annotations`** y type hints completos en
  todos los módulos.
- **Constantes nombradas** (`PERSONALIDADES`, `REGIONES`,
  `MAX_INTENTOS`, `MIN_ENVIOS`/`MAX_ENVIOS`) en vez de literales
  repartidos.

---

## 5. Archivos de soporte creados

- **`requirements.txt`** (estaba vacío) con las versiones reales:
  `playwright==1.60.0`, `rich==15.0.0`, `faker==40.23.0`.
- **`.gitignore`**: excluye `.venv/`, `__pycache__/`, `logs/`,
  `*.csv`, `*.json`, `*.7z`.
- **`tests/test_logica.py`**: 16 tests (ver §6).
- **`README.md`** reescrito con instalación, uso, estructura y
  explicación de la "IA sencilla".
- **`logger.py` eliminado**: estaba vacío y su función (escribir
  CSV/JSON) ya vive en `main.py`. Mantener un archivo vacío induce a
  error.

---

## 6. Tests (16, todos en verde)

`python3 -m pytest -v`

Cubren:

- Personas: campos válidos, tamaño de grupo, coherencia edad↔grupo.
- Respuestas: **ninguna vacía** (lo que causaba envíos fallidos),
  escala dentro de rango, `rango_forzado` de P9/P10, validez de
  opción múltiple y de checkboxes, exclusividad de "Ninguna",
  variación entre personas (>50 firmas distintas en 100).
- `normalizar_url`: 4 variantes (`/edit`, parámetros, `/`, ya limpia).
- Integridad del `config.py`: IDs consecutivos y **pesos que cuadran
  con el número de opciones** (test que blindó el config).

> La capa Playwright no se testea automáticamente (requiere red y un
> formulario en vivo); se valida ejecutando `main.py` con
> `Diagnóstico = s`.

---

## 7. Verificación recomendada en la máquina del usuario

```bash
source .venv/bin/activate
pip install -r requirements.txt
pip install pytest
python3 -m pytest -v                 # 16 en verde
python3 main.py                      # 3 envíos, velocidad normal, diagnóstico s
```

Esperado en diagnóstico: cada pregunta marcada con ✅, luego
`✅ Navegó a /formResponse — envío confirmado`, y el contador del
formulario subiendo en la cuenta exacta de envíos exitosos.
