# Diseño Técnico — Bot de Producción & Bodega
## Pepe Pez | JOPACA S.A.S.
**Versión:** 1.0 | **Fecha:** Junio 2026

---

## 1. Resumen Ejecutivo

Bot de Telegram que escucha el grupo **Bodega&Producción PPpez**, clasifica automáticamente cada mensaje con foto, extrae el peso de las fotos de balanza mediante OCR, y registra todo en Google Sheets como bitácora operacional. El staff no cambia su flujo de trabajo. El bot responde en el grupo con un resumen detallado de cada registro.

---

## 2. Stack Tecnológico

| Componente | Tecnología | Justificación |
|------------|-----------|---------------|
| Bot framework | `python-telegram-bot` v21 | Async, estable, amplia documentación |
| Servidor web | `Flask` | Webhook handler, liviano |
| OCR balanzas | `Google Cloud Vision API` | Precisión alta en displays digitales |
| OCR fallback | `Tesseract + Pillow` | Sin costo, para imágenes limpias |
| Base de datos | `PostgreSQL` | Registros, whitelist, tickets, estado |
| Google Sheets | `gspread` + `Google Sheets API v4` | Bitácora accesible para admins |
| Scheduler | `APScheduler` | Resúmenes diarios automáticos |
| Servidor | VPS Linux (Ubuntu 22.04) | El mismo donde corre Flask actual |
| Variables de entorno | `.env` + `python-dotenv` | Seguridad credenciales |

---

## 3. Arquitectura General

```
[Grupo Telegram: Bodega&Producción]
        │
        │  Webhook (HTTPS)
        ▼
┌─────────────────────────────────┐
│         Flask App               │
│  /webhook  endpoint             │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│      MessageProcessor           │
│  1. Verificar whitelist         │
│  2. Validar foto presente       │
│  3. Clasificar tipo de registro │
│  4. Extraer peso (OCR)          │
│  5. Completar datos faltantes   │
└──────────────┬──────────────────┘
               │
       ┌───────┴───────┐
       ▼               ▼
┌──────────┐    ┌──────────────┐
│PostgreSQL│    │Google Sheets │
│(estado,  │    │(bitácora     │
│ tickets, │    │ operacional) │
│whitelist)│    └──────────────┘
└──────────┘
       │
       ▼
┌─────────────────────────────────┐
│     ResponseBuilder             │
│  Genera respuesta detallada     │
│  Envía al grupo de producción   │
│  Escala novedades a admins      │
└─────────────────────────────────┘
```

---

## 4. Estructura de la Base de Datos (PostgreSQL)

### 4.1 Tabla `users` — Lista blanca
```sql
CREATE TABLE users (
    id              SERIAL PRIMARY KEY,
    telegram_id     BIGINT UNIQUE NOT NULL,
    name            VARCHAR(100) NOT NULL,
    role            VARCHAR(50) NOT NULL,  -- 'staff', 'admin', 'supervisor'
    area            VARCHAR(50),           -- 'produccion', 'bodega'
    active          BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT NOW(),
    removed_at      TIMESTAMP
);
```

### 4.2 Tabla `records` — Bitácora principal
```sql
CREATE TABLE records (
    id              SERIAL PRIMARY KEY,
    record_code     VARCHAR(20) UNIQUE,    -- PRD-0001, MRM-0001, etc.
    chat_id         BIGINT NOT NULL,
    message_id      BIGINT NOT NULL,
    telegram_user_id BIGINT NOT NULL,
    record_type     VARCHAR(50) NOT NULL,  -- 'ingreso_mp', 'merma', etc.
    product         VARCHAR(150),
    weight_kg       DECIMAL(8,3),
    weight_source   VARCHAR(20),           -- 'ocr', 'manual', 'texto'
    unit            VARCHAR(20),           -- 'kg', 'px', 'lt', 'und'
    quantity        INTEGER,
    destination     VARCHAR(100),          -- para despachos
    supplier        VARCHAR(100),          -- para ingresos MP
    file_id         TEXT,                  -- Telegram file_id de la foto
    notes           TEXT,
    status          VARCHAR(20) DEFAULT 'ok',
    corrected_by    INTEGER REFERENCES records(id),
    created_at      TIMESTAMP DEFAULT NOW()
);
```

### 4.3 Tabla `tickets` — Novedades y mantenimiento
```sql
CREATE TABLE tickets (
    id              SERIAL PRIMARY KEY,
    ticket_code     VARCHAR(20) UNIQUE,    -- NOV-0001, MNT-0001
    record_id       INTEGER REFERENCES records(id),
    ticket_type     VARCHAR(30),           -- 'calidad', 'mantenimiento', 'proveedor'
    description     TEXT NOT NULL,
    reported_by     BIGINT NOT NULL,
    supplier        VARCHAR(100),
    status          VARCHAR(20) DEFAULT 'abierto',  -- 'abierto', 'en_proceso', 'resuelto'
    resolved_by     BIGINT,
    resolution_notes TEXT,
    opened_at       TIMESTAMP DEFAULT NOW(),
    resolved_at     TIMESTAMP
);
```

### 4.4 Tabla `pending_responses` — Flujo de preguntas del bot
```sql
CREATE TABLE pending_responses (
    id              SERIAL PRIMARY KEY,
    chat_id         BIGINT NOT NULL,
    user_id         BIGINT NOT NULL,
    waiting_for     VARCHAR(50) NOT NULL,  -- 'weight', 'product', 'destination'
    partial_data    JSONB,
    expires_at      TIMESTAMP,
    created_at      TIMESTAMP DEFAULT NOW()
);
```

---

## 5. Estructura Google Sheets

### Libro: `Bitácora Producción PPpez`

**Hoja 1: `Registros`**
| Columna | Campo | Ejemplo |
|---------|-------|---------|
| A | Código | PRD-2847 |
| B | Fecha | 25/06/2026 |
| C | Hora | 09:12 |
| D | Tipo | Procesado |
| E | Producto | Tentáculo limpio |
| F | Peso (kg) | 15.389 |
| G | Unidad | kg |
| H | Cantidad (px/und) | — |
| I | Colaborador | Anthony Pier |
| J | Área | Producción |
| K | Destino local | — |
| L | Proveedor | — |
| M | Producción destino | Bollos |
| N | Fuente del peso | OCR |
| O | file_id Telegram | AgACAgIAAxk... |
| P | Notas | — |
| Q | Estado | ✅ OK |

**Hoja 2: `Tickets Novedades`**
| Columna | Campo |
|---------|-------|
| A | Código ticket |
| B | Fecha apertura |
| C | Tipo |
| D | Producto afectado |
| E | Descripción |
| F | Reportado por |
| G | Proveedor |
| H | Estado |
| I | Fecha resolución |
| J | Resolución |

**Hoja 3: `Resumen Diario`** ← generada automáticamente cada noche

---

## 6. Tipos de Registro (16 tipos)

| # | Tipo | Código | Foto | Peso |
|---|------|--------|------|------|
| 1 | Ingreso MP | PRD-XXXX | ✅ Obligatoria | ✅ Obligatorio |
| 2 | Porcionado | POR-XXXX | ✅ Obligatoria | ✅ Obligatorio |
| 3 | Cocción | COC-XXXX | ✅ Obligatoria | ✅ Obligatorio |
| 4 | Apanado | APN-XXXX | ✅ Obligatoria | ✅ Obligatorio |
| 5 | Merma | MRM-XXXX | ✅ Obligatoria | ✅ Obligatorio |
| 6 | Devolución/Baja | DEV-XXXX | ✅ Obligatoria | ✅ Obligatorio |
| 7 | Despacho a locales | DSP-XXXX | ✅ Obligatoria | ✅ Obligatorio |
| 8 | Novedad de calidad | NOV-XXXX | ✅ Obligatoria | ❌ No aplica |
| 9 | Apertura bodega/local | APE-XXXX | ✅ Obligatoria | ❌ No aplica |
| 10 | Cierre bodega/local | CIE-XXXX | ✅ Obligatoria | ❌ No aplica |
| 11 | Limpieza | LMP-XXXX | ✅ Obligatoria | ❌ No aplica |
| 12 | Inventario/Stock | INV-XXXX | ✅ Obligatoria | ✅ Obligatorio |
| 13 | Mantenimiento equipo | MNT-XXXX | ✅ Obligatoria | ❌ No aplica |
| 14 | Prueba de producto | PRB-XXXX | ✅ Obligatoria | ❌ No aplica |
| 15 | Corrección de registro | COR-XXXX | ✅ Obligatoria | Opcional |
| 16 | MP Utilizada en producción | MPU-XXXX | ✅ Obligatoria | ✅ Obligatorio |

> Regla única: **Sin foto no hay registro**. El bot rechaza cualquier mensaje sin foto adjunta.

---

## 7. Clasificador de Mensajes

El bot identifica el tipo de registro analizando el texto del caption de la foto:

```python
TIPO_KEYWORDS = {
    'ingreso_mp': [
        'ingresa', 'ingresan', 'ingreso', 'entra'
    ],
    'merma': [
        'merma', 'descarte', 'baja merma'
    ],
    'porcionado': [
        'para porcionar', 'porcionado', 'porcionar'
    ],
    'coccion': [
        'cocido', 'cocinado', 'cocción', 'para cocer'
    ],
    'apanado': [
        'para apanar', 'apanado', 'apanados', 'apanar'
    ],
    'despacho': [
        'sale para', 'despacho', 'sale a', 'envío a local'
    ],
    'merma_proceso': [
        'merma de', 'merma del'
    ],
    'devolucion': [
        'devolución', 'devolver', 'entra a devolución', 'se da de baja'
    ],
    'novedad_calidad': [
        'se reporta', 'llega con', 'contaminado', 'mal olor',
        'dañado', 'pelos', 'cabellos', 'mal estado'
    ],
    'apertura': [
        'abriendo', 'apertura', 'ingresando al local'
    ],
    'cierre': [
        'cerrando', 'cierre', 'cerramos'
    ],
    'limpieza': [
        'limpieza', 'limpio', 'fumigación', 'desinfección'
    ],
    'mantenimiento': [
        'dañado', 'no funciona', 'revisión', 'mantenimiento', 'falla'
    ],
    'inventario': [
        'quedan', 'stock', 'en inventario', 'hay en bodega'
    ],
    'prueba': [
        'prueba', 'degustación', 'test', 'para probar'
    ],
    'requerimiento': [
        'requerimiento', 'pedido proveedor', 'solicitud'
    ],
    'mp_utilizada': [
        'para producir', 'utilizado', 'utilizada', 'usado para',
        'para elaborar', 'para preparar', 'consumido', 'se usó'
    ],
}
```

Si el texto no coincide con ninguna categoría, el bot pregunta:
```
No reconocí el tipo de registro.
¿Es una de estas opciones?
[1] Ingreso MP  [2] Merma  [3] Porcionado
[4] Despacho   [5] Novedad  [6] Otro
```

---

## 8. Módulo OCR para Balanzas

```python
# ocr_balance.py

from google.cloud import vision
import re

def extract_weight_from_image(image_bytes: bytes) -> dict:
    """
    Extrae el peso de una foto de balanza digital.
    Retorna: {'weight': 15.389, 'unit': 'kg', 'confidence': 'high'}
    """
    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=image_bytes)
    response = client.text_detection(image=image)

    texts = [t.description for t in response.text_annotations]
    full_text = ' '.join(texts).lower()

    # Patrones comunes en balanzas de cocina
    patterns = [
        r'(\d+[\.,]\d{1,3})\s*kg',
        r'(\d+[\.,]\d{1,3})\s*lb',
        r'net[:\s]*(\d+[\.,]\d{1,3})',
        r'(\d{1,3}[\.,]\d{3})',  # formato 15.389
    ]

    for pattern in patterns:
        match = re.search(pattern, full_text)
        if match:
            weight_str = match.group(1).replace(',', '.')
            return {
                'weight': float(weight_str),
                'unit': 'kg' if 'lb' not in full_text else 'lb',
                'confidence': 'high',
                'raw_text': full_text
            }

    return {'weight': None, 'confidence': 'failed', 'raw_text': full_text}
```

**Fallback si OCR falla:** El bot pregunta el peso directamente al colaborador en el grupo. El colaborador responde solo el número y el bot completa el registro.

---

## 9. Flujo Completo de un Mensaje

```
1. Llega mensaje al grupo con foto + caption
2. Bot verifica: ¿user_id está en whitelist? → NO: ignora silenciosamente
3. Bot verifica: ¿tiene foto? → NO: responde "Falta la foto..."
4. Bot descarga la foto desde Telegram (guarda file_id, NO descarga permanente)
5. Bot clasifica el tipo de registro por keywords en el caption
6. Si el tipo requiere peso:
   a. Intenta OCR en la foto
   b. Si OCR exitoso → usa ese peso
   c. Si OCR falla → pregunta al colaborador
7. Bot extrae producto del caption (NLP simple o regex)
8. Si el tipo es despacho → verifica si menciona local de destino
   a. Si no menciona → pregunta al colaborador
9. Construye el registro completo
10. Guarda en PostgreSQL → genera código único (PRD-XXXX, MRM-XXXX, MPU-XXXX, etc.)
11. Guarda en Google Sheets
12. Responde en el grupo con confirmación detallada
13. Si es novedad/mantenimiento → crea ticket + notifica al grupo de admins
```

---

## 10. Respuestas del Bot por Tipo

### Ingreso de Materia Prima
```
✅ INGRESO REGISTRADO
━━━━━━━━━━━━━━━━━━━━━━━
📦 Producto: Pulpo parrilla
⚖️  Peso: 39 px
👤 Colaborador: Anthony Pier
🕐 Hora: 11:55
📅 Fecha: 18/06/2026
📍 Área: Producción - Ceibos
🗂️ Código: PRD-2847
━━━━━━━━━━━━━━━━━━━━━━━
Guardado en bitácora ✓
```

### Merma
```
📉 MERMA REGISTRADA
━━━━━━━━━━━━━━━━━━━━━━━
📦 Producto: Tentáculo limpio
⚖️  Merma: 7.250 kg
👤 Colaborador: Anthony Pier
🕐 Hora: 09:31
📅 Fecha: 24/06/2026
🗂️ Código: MRM-0341
━━━━━━━━━━━━━━━━━━━━━━━
Guardado en bitácora ✓
```

### Novedad de Calidad
```
🚨 NOVEDAD REGISTRADA
━━━━━━━━━━━━━━━━━━━━━━━
📦 Producto: Mondongo
⚠️  Detalle: Llega con pelos
👤 Reportado por: Anthony Pier
🕐 Hora: 07:14
📅 Fecha: 25/06/2026
📋 Ticket: NOV-0089 — ABIERTO
━━━━━━━━━━━━━━━━━━━━━━━
⚡ Administración notificada
```

### MP Utilizada en Producción
```
🔄 MP UTILIZADA REGISTRADA
━━━━━━━━━━━━━━━━━━━━━━━━━
📦 MP: Verde
⚖️  Cantidad usada: 15.03 kg
🍳 Para producir: Bollos
👤 Colaborador: Melissan Delgado
🕐 Hora: 06:29
📅 Fecha: 22/06/2026
🗂️ Código: MPU-0012
━━━━━━━━━━━━━━━━━━━━━━━━━
Guardado en bitácora ✓
```

### Apertura / Cierre
```
🔓 APERTURA REGISTRADA
━━━━━━━━━━━━━━━━━━━━━━━
📍 Local: Ceibos
👤 Colaborador: Jostin Pppz
🕐 Hora: 06:09
📅 Fecha: 25/06/2026
🗂️ Código: APE-0198
━━━━━━━━━━━━━━━━━━━━━━━
Guardado en bitácora ✓
```

---

## 11. Comandos del Bot (solo en grupo de Admins)

| Comando | Función |
|---------|---------|
| `/reporte hoy` | Resumen del día en curso |
| `/reporte 24/06` | Resumen de una fecha específica |
| `/reporte semana` | Resumen semanal |
| `/tickets abiertos` | Lista de novedades sin resolver |
| `/resolver NOV-0089` | Cierra un ticket de novedad |
| `/activar @usuario` | Agrega a whitelist |
| `/desactivar @usuario` | Remueve de whitelist |
| `/buscar pulpo` | Busca todos los registros de un producto |
| `/mermas hoy` | Listado de mermas del día |
| `/corrregir PRD-2847` | Inicia flujo de corrección de un registro |

---

## 12. Resumen Automático Diario (APScheduler)

Todos los días a las **21:00** el bot envía al grupo de admins:

```
📊 RESUMEN PRODUCCIÓN — 25/06/2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📥 INGRESOS (12 registros)
• Camarón apanado — 100 px — Anthony
• Aros calamar — 140 px — Erika
• Pulpa cangrejo — 220 px — Anthony
• ...

📉 MERMAS (5 registros)
• Tentáculo cocido — 7.250 kg
• Corvina — 2 registros
• Cebolla colorada — 0.420 kg
• ...

🚨 NOVEDADES ACTIVAS (2)
• NOV-0089 — Mondongo con pelos — ABIERTO 2 días
• NOV-0091 — Aro contaminado — ABIERTO hoy

🔄 MP UTILIZADA (8 registros)
• Verde — 15.03 kg → Bollos
• Camarón — 2.13 kg → Camarón apanado
• Corvina — 4.50 kg → Filete plancha
• ...

🔓 Apertura: 06:09 — Jostin
🔒 Cierre: 18:06 — Jostin

📊 Total registros del día: 47
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Ver detalle completo en Google Sheets ↗
```

---

## 13. Seguridad

**Lista blanca (whitelist):**
- Solo `telegram_id` registrados en la tabla `users` son procesados
- Cualquier mensaje de ID no registrado es ignorado silenciosamente
- El bot no responde ni reacciona a mensajes de no autorizados

**Gestión de bajas:**
```
Admin escribe en grupo admins: /desactivar @Anthony
Bot: ✅ Anthony Pier removido de lista blanca.
     Sus registros históricos se conservan.
     A partir de ahora sus mensajes son ignorados.
```

**Seguridad adicional:**
- Webhook con token secreto en header
- HTTPS obligatorio (Let's Encrypt en el VPS)
- Variables sensibles en `.env` (nunca en código)
- Bot Token, Google credentials, DB password — todos en `.env`
- Rate limiting por `user_id`: máx 30 mensajes/minuto por colaborador

---

## 14. Estructura de Archivos del Proyecto

```
bot_produccion_ppez/
│
├── .env                        # Variables de entorno (NO en git)
├── .gitignore
├── requirements.txt
├── README.md
│
├── app.py                      # Flask app + webhook entry point
│
├── bot/
│   ├── __init__.py
│   ├── handlers.py             # Handlers de mensajes Telegram
│   ├── classifier.py           # Clasificador de tipos de registro
│   ├── responses.py            # Generador de respuestas detalladas
│   └── commands.py             # Comandos /reporte, /tickets, etc.
│
├── services/
│   ├── __init__.py
│   ├── ocr_service.py          # OCR balanzas (Vision API + Tesseract)
│   ├── sheets_service.py       # Google Sheets writer
│   ├── ticket_service.py       # Gestión de tickets de novedades
│   └── scheduler_service.py    # Resúmenes diarios automáticos
│
├── models/
│   ├── __init__.py
│   ├── user.py                 # Modelo User / whitelist
│   ├── record.py               # Modelo Record / bitácora
│   └── ticket.py               # Modelo Ticket / novedades
│
├── database/
│   ├── connection.py           # Pool de conexión PostgreSQL
│   └── migrations/
│       ├── 001_create_users.sql
│       ├── 002_create_records.sql
│       └── 003_create_tickets.sql
│
└── utils/
    ├── __init__.py
    ├── code_generator.py       # Genera PRD-XXXX, MRM-XXXX, etc.
    └── validators.py           # Validaciones de entrada
```

---

## 15. Variables de Entorno (.env)

```env
# Telegram
TELEGRAM_BOT_TOKEN=
TELEGRAM_WEBHOOK_SECRET=
GRUPO_PRODUCCION_CHAT_ID=
GRUPO_ADMINS_CHAT_ID=

# Base de datos
DATABASE_URL=postgresql://user:password@localhost:5432/ppez_produccion

# Google APIs
GOOGLE_APPLICATION_CREDENTIALS=./credentials/google_service_account.json
GOOGLE_SHEETS_ID=

# OCR
USE_CLOUD_VISION=true          # false = solo Tesseract local

# Configuración
RESUMEN_HORA=21:00
TIMEZONE=America/Guayaquil
DEBUG=false
```

---

## 16. Fases de Implementación

### Fase 1 — MVP (2-3 semanas)
- Whitelist funcional
- Bot escucha el grupo
- Clasificador básico por keywords
- Registro en PostgreSQL + Google Sheets
- Respuesta detallada en el grupo
- Comandos `/reporte` básicos en grupo admins

### Fase 2 — OCR y tickets (1-2 semanas adicionales)
- OCR de balanzas con Google Vision API
- Sistema de tickets para novedades
- Notificación automática a admins cuando hay novedad
- Comando `/resolver` para cerrar tickets

### Fase 3 — Automatización (1 semana adicional)
- Resumen diario automático a las 21:00
- Alerta si no hay apertura registrada antes de las 07:00
- Alerta si no hay cierre registrado antes de las 19:00

### Fase 4 — Inteligencia (futuro)
- Clasificador mejorado con IA (modelo de lenguaje ligero)
- Detección de proveedores recurrentes con novedades
- Análisis de mermas por producto y período
- Dashboard web para consulta de bitácora

---

## 17. Costos Estimados de Operación

| Servicio | Costo mensual estimado |
|----------|----------------------|
| VPS (ya existente) | $0 adicional |
| Google Cloud Vision API | ~$3-8 USD (500-1500 imágenes/mes) |
| Google Sheets API | Gratis |
| PostgreSQL (mismo VPS) | $0 adicional |
| **Total adicional** | **~$5-10 USD/mes** |

---

*Documento generado para JOPACA S.A.S. — Uso interno Pepe Pez*
