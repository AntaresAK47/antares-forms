# 🪟 Guía de Instalación y Ejecución en Windows

Esta guía cubre todo lo necesario para ejecutar **Antares Forms**
en Windows 10 o Windows 11 desde cero, paso a paso, sin omitir
ningún detalle.

---

## ⚠️ Modificación de Código Obligatoria

Antes de cualquier instalación, hay **un cambio de código imprescindible**.
El proyecto está configurado con la ruta de Chromium de Linux
(`/usr/bin/chromium-browser`) que no existe en Windows. Sin este cambio,
el programa fallará al intentar abrir el navegador.

Abrid `src/form_filler.py` con cualquier editor de texto y localizad
estas líneas cerca del principio del archivo:

```python
CHROMIUM_PATH = "/usr/bin/chromium-browser"

LAUNCH_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
]
```

Reemplazadlas exactamente por esto:

```python
import sys

# Detección automática de plataforma
_ES_WINDOWS = sys.platform == "win32"

# En Windows: Playwright descarga y gestiona su propio Chromium.
# En Linux:   Se usa el Chromium del sistema (snap en Ubuntu 26.04).
CHROMIUM_PATH = None if _ES_WINDOWS else "/usr/bin/chromium-browser"

# Los argumentos de sandbox solo son necesarios en Linux.
LAUNCH_ARGS = [] if _ES_WINDOWS else [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
]
```

Luego localizad la función `enviar_respuesta` y dentro de ella el bloque
`p.chromium.launch(...)`. Reemplazad ese bloque por:

```python
opciones_launch = dict(
    headless=cfg["headless"],
    slow_mo=perfil.slow_mo,
    args=LAUNCH_ARGS,
)
if CHROMIUM_PATH:
    opciones_launch["executable_path"] = CHROMIUM_PATH

browser = p.chromium.launch(**opciones_launch)
```

Guardad el archivo. Con este cambio el proyecto detectará
automáticamente si corre en Windows o Linux y se configurará solo.

---

## Requisitos Previos

### Python 3.10 o superior

1. Id a <https://www.python.org/downloads/windows/>
2. Descargad el instalador de la versión más reciente (3.12 o 3.13).
3. Ejecutad el instalador y en la primera pantalla marcad
   obligatoriamente la casilla:
   ```
   ☑ Add Python to PATH
   ```
   Sin esa casilla marcada, nada de lo que sigue funcionará.
4. Elegid **"Install Now"** y completad la instalación.

Verificad en una terminal nueva:

```powershell
python --version
```

Resultado esperado: `Python 3.12.x` o superior.

> Si el comando no se reconoce, cerrad y volved a abrir la terminal,
> o reiniciad el equipo. Si persiste, el PATH no se configuró
> correctamente: desinstalad Python y repetid marcando la casilla.

---

### Git para Windows

1. Id a <https://git-scm.com/download/win>
2. Descargad el instalador de 64 bits.
3. Durante la instalación podéis dejar todas las opciones por defecto.
   La opción recomendada para el editor es **"Use Visual Studio Code
   as Git's default editor"** si tenéis VS Code instalado.
4. Completad la instalación.

Verificad:

```powershell
git --version
```

Resultado esperado: `git version 2.4x.x.windows.x`

---

## Paso 1 — Clonar el Repositorio

Abrid **PowerShell** o **Símbolo del sistema** y ejecutad:

```powershell
git clone https://github.com/AntaresAK47/antares-forms.git
cd antares-forms
```

---

## Paso 2 — Crear el Entorno Virtual

```powershell
python -m venv .venv
```

---

## Paso 3 — Activar el Entorno Virtual

En **PowerShell:**

```powershell
.venv\Scripts\Activate.ps1
```

En **Símbolo del sistema (cmd):**

```cmd
.venv\Scripts\activate.bat
```

**Resultado esperado:** veréis `(.venv)` al inicio de la línea:

```
(.venv) PS C:\ruta\antares-forms>
```

> **Error frecuente en PowerShell:**
> Si aparece `"No se puede cargar el archivo porque la ejecución de
> scripts está deshabilitada"`, ejecutad primero:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```
> Responded `S` cuando pregunte confirmación y repetid la activación.

---

## Paso 4 — Instalar las Dependencias

Con el entorno virtual activo:

```powershell
python -m pip install --upgrade pip
python -m pip install playwright rich faker pytest
```

---

## Paso 5 — Instalar Chromium para Playwright

En Windows, Playwright descarga su propio Chromium directamente
sin necesidad de instalarlo por separado en el sistema:

```powershell
playwright install chromium
```

Este comando descargará unos 150 MB. Esperad a que termine.

Verificad:

```powershell
python -c "from playwright.sync_api import sync_playwright; print('✅ Playwright listo')"
```

---

## Paso 6 — Verificar Todo

```powershell
python -c "import playwright, rich, faker; print('✅ Todo instalado')"
```

---

## Paso 7 — Ejecutar los Tests

```powershell
python -m pytest tests/ -v
```

**Resultado esperado:** `16 passed`

Si algún test falla, comprobad que realizasteis la modificación de
código descrita al inicio de esta guía.

---

## Paso 8 — Ejecutar el Proyecto

```powershell
python main.py
```

El programa os pedirá de forma interactiva:

| Parámetro | Descripción |
|---|---|
| **URL** | Enlace público del formulario (debe terminar en `/viewform`) |
| **Cantidad** | Número de veces que se responderá (1–500) |
| **Velocidad** | `rapida`, `normal` o `humana` |
| **¿Ver el navegador?** | `s` para visible, `n` para oculto (headless) |
| **¿Diagnóstico?** | `s` para ver el detalle de cada paso |

Para la primera prueba se recomienda responder `s` al navegador
y `s` al diagnóstico, y poner `1` como cantidad, para verificar
visualmente que todo funciona.

---

## Alternativa con uv (Instalación Moderna)

Si preferís usar uv, el gestor moderno de dependencias:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Cerrad y volved a abrir la terminal, luego:

```powershell
uv sync
playwright install chromium
uv run python main.py
```

Para los tests:

```powershell
uv run pytest tests/ -v
```

---

## Errores Comunes en Windows

### `python` no se reconoce como comando

Python no está en el PATH. Desinstalad y reinstalad marcando
**"Add Python to PATH"** en el primer paso del instalador.

### `playwright` no se reconoce como comando

El entorno virtual no está activo. Ejecutad `.venv\Scripts\Activate.ps1`
(PowerShell) o `.venv\Scripts\activate.bat` (cmd) antes de cualquier
comando, y verificad que veis `(.venv)` en el prompt.

### El navegador se abre pero no llena el formulario

Verificad que realizasteis el cambio en `src/form_filler.py`
descrito al principio de esta guía. Sin ese cambio, el código
intentará usar la ruta de Linux que no existe en Windows.

### Error de `ModuleNotFoundError`

El entorno virtual no está activo o las dependencias no están
instaladas en él. Verificad `(.venv)` en el prompt y repetid
el Paso 4.

### `playwright install chromium` tarda mucho

Es normal: descarga ~150 MB. Aseguraos de tener conexión estable
y esperad a que termine completamente.

---

## Verificación Final

Si el programa imprime esto al terminar, todo funcionó correctamente:

```
🏆 SIMULACIÓN COMPLETADA

✅ Exitosos:  N / N
❌ Fallidos:   0 / N
```

Y podéis comprobar que las respuestas aparecieron en vuestro
Google Forms actualizando la pestaña de Respuestas.
