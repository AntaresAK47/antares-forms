# =============================================================
# ANTARES FORMS — Configuración de la Encuesta Real
# Archivo: src/config.py
# Descripción: Preguntas reales del formulario de phishing
# =============================================================

ENCUESTA = {
    "titulo": "Encuesta sobre Phishing y Ciberseguridad",
    "preguntas": [
        {
            "id": 1,
            "texto": "¿Con qué frecuencia utiliza servicios digitales institucionales como correo, plataformas, formularios o portales web?",
            "tipo": "opcion_multiple",
            "opciones": ["Nunca", "Rara vez", "A veces", "Frecuentemente", "Siempre"],
            "pesos": {
                "grupo_edad_joven":  [5,  10, 20, 35, 30],
                "grupo_edad_adulto": [3,  8,  20, 40, 29],
                "grupo_edad_maduro": [8,  15, 25, 32, 20],
                "grupo_edad_mayor":  [15, 20, 30, 25, 10],
            }
        },
        {
            "id": 2,
            "texto": "¿Con qué frecuencia recibe correos, mensajes o enlaces que considera sospechosos?",
            "tipo": "opcion_multiple",
            "opciones": ["Nunca", "Rara vez", "A veces", "Frecuentemente", "Siempre"],
        },
        {
            "id": 3,
            "texto": "Antes de abrir un enlace, ¿verifica el dominio o dirección URL?",
            "tipo": "opcion_multiple",
            "opciones": ["Nunca", "Rara vez", "A veces", "Frecuentemente", "Siempre"],
            "pesos": {
                "educacion_basico":        [25, 30, 25, 15, 5],
                "educacion_medio":         [10, 20, 30, 25, 15],
                "educacion_universitario": [5,  10, 25, 35, 25],
                "educacion_posgrado":      [2,  5,  18, 35, 40],
            }
        },
        {
            "id": 4,
            "texto": "¿Qué señales suele revisar para identificar un posible phishing? Puede marcar varias.",
            "tipo": "checkboxes",
            "opciones": ["Remitente", "URL", "Urgencia", "Errores", "Solicitud de datos", "Diseño", "Ninguna"],
            "pesos_seleccion": {
                # Probabilidad (0.0-1.0) de seleccionar cada opción según educación
                "educacion_basico":        [0.20, 0.15, 0.10, 0.10, 0.10, 0.05, 0.60],
                "educacion_medio":         [0.35, 0.30, 0.25, 0.20, 0.20, 0.10, 0.20],
                "educacion_universitario": [0.60, 0.65, 0.45, 0.40, 0.50, 0.25, 0.05],
                "educacion_posgrado":      [0.80, 0.85, 0.65, 0.60, 0.70, 0.45, 0.02],
            }
        },
        {
            "id": 5,
            "texto": "¿Qué tan seguro se siente identificando una URL sospechosa?",
            "tipo": "escala",
            "min": 1,
            "max": 5,
        },
        {
            "id": 6,
            "texto": "Si recibe un mensaje que solicita verificar credenciales, ¿Qué haría primero?",
            "tipo": "opcion_multiple",
            "opciones": ["Abrir enlace", "Consultar la fuente oficial", "Ignorar", "Reenviar", "No sabe"],
            "pesos": {
                "educacion_basico":        [30, 20, 15, 10, 25],
                "educacion_medio":         [15, 35, 25, 10, 15],
                "educacion_universitario": [5,  55, 30, 5,  5],
                "educacion_posgrado":      [2,  65, 25, 3,  5],
            }
        },
        {
            "id": 7,
            "texto": "¿Qué nivel de riesgo considera que representa el phishing para instituciones?",
            "tipo": "escala",
            "min": 1,
            "max": 5,
        },
        {
            "id": 8,
            "texto": "¿Confía en filtros o sistemas automáticos para ayudar a detectar phishing?",
            "tipo": "escala",
            "min": 1,
            "max": 5,
        },
        {
            "id": 9,
            "texto": "¿Considera necesaria mayor capacitación en ciberseguridad y phishing?",
            "tipo": "escala",
            "min": 1,
            "max": 5,
            "rango_forzado": [3, 5],
        },
        {
            "id": 10,
            "texto": "¿Aceptaría usar una herramienta que analice texto y URL para advertir posibles casos de phishing?",
            "tipo": "escala",
            "min": 1,
            "max": 5,
            "rango_forzado": [3, 5],
        },
    ]
}