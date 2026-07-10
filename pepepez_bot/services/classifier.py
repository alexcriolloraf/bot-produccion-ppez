import re

KEYWORDS = {
    'apertura': ['abriendo', 'apertura', 'abrimos', 'ingresando', 'buenos dias'],
    'cierre': ['cerrando', 'cierre', 'cerramos', 'cerrado'],
    'devolucion': ['se da de baja', 'devolucion', 'baja', 'se bota', 'se descarta'],
    'novedad_calidad': ['cabellos', 'pelos', 'se reporta', 'mal olor', 'danado', 'contaminado', 'mal estado', 'vencido'],
    'merma': ['merma de', 'merma del', 'merma'],
    'mantenimiento': ['se quemo', 'no funciona', 'revision', 'mantenimiento', 'falla', 'roto'],
    'despacho': ['sale para', 'despacho', 'sale a', 'px mix', 'mix canasta'],
    'porcionado': ['para porcionar', 'porcionado', 'porcionar'],
    'coccion': ['cocido', 'cocinado', 'coccion', 'para cocer', 'cocida', 'cocinada'],
    'apanado': ['para apanar', 'apanado', 'apanar', 'apanada'],
    'mp_utilizada': [
        'para bollos', 'para canasta', 'para receta', 'para elaborar',
        'para preparar', 'para croquetas', 'para empanadas', 'para mix',
        'para relleno', 'para salsa', 'para sopa', 'para ceviche',
        'para corviche', 'para tigrillo', 'para patacones', 'para ensalada'
    ],
    'limpieza': ['limpieza', 'limpio', 'fumigacion', 'desinfeccion', 'lavado'],
    'inventario': ['quedan', 'stock', 'en inventario', 'hay en bodega'],
    'ingreso_mp': ['ingresa', 'ingresan', 'ingreso', 'llego', 'recibido', 'entrada de'],
}

RECORD_CODES = {
    'ingreso_mp':      'PRD',
    'porcionado':      'POR',
    'coccion':         'COC',
    'apanado':         'APN',
    'merma':           'MRM',
    'devolucion':      'DEV',
    'despacho':        'DSP',
    'novedad_calidad': 'NOV',
    'apertura':        'APE',
    'cierre':          'CIE',
    'limpieza':        'LMP',
    'inventario':      'INV',
    'mantenimiento':   'MNT',
    'mp_utilizada':    'MPU',
}

def extract_weight_from_text(text: str) -> dict:
    """
    Extrae peso de cualquier texto.
    Reconoce: kg, g, gr, gramos, lb, lbs, libras, oz, onzas, px, porciones, unidades, und, lt, ml
    Ejemplos:
        "11.50lb" -> 11.50 lb
        "500gr" -> 500 gr
        "2.5kg" -> 2.5 kg
        "39px" -> 39 px
        "200ml" -> 200 ml
    """
    text_lower = text.lower().strip()

    patrones = [
        # Kilogramos
        (r'(\d+[\.,]\d+)\s*kilogramos?', 'kg'),
        (r'(\d+[\.,]\d+)\s*kg', 'kg'),
        (r'(\d+)\s*kilogramos?', 'kg'),
        (r'(\d+)\s*kg', 'kg'),
        # Gramos
        (r'(\d+[\.,]\d+)\s*gramos?', 'gr'),
        (r'(\d+[\.,]\d+)\s*grs?', 'gr'),
        (r'(\d+)\s*gramos?', 'gr'),
        (r'(\d+)\s*grs?', 'gr'),
        # Libras
        (r'(\d+[\.,]\d+)\s*libras?', 'lb'),
        (r'(\d+[\.,]\d+)\s*lbs?', 'lb'),
        (r'(\d+)\s*libras?', 'lb'),
        (r'(\d+)\s*lbs?', 'lb'),
        # Onzas
        (r'(\d+[\.,]\d+)\s*onzas?', 'oz'),
        (r'(\d+[\.,]\d+)\s*oz', 'oz'),
        (r'(\d+)\s*onzas?', 'oz'),
        (r'(\d+)\s*oz', 'oz'),
        # Litros
        (r'(\d+[\.,]\d+)\s*litros?', 'lt'),
        (r'(\d+[\.,]\d+)\s*lts?', 'lt'),
        (r'(\d+)\s*litros?', 'lt'),
        (r'(\d+)\s*lts?', 'lt'),
        # Mililitros
        (r'(\d+)\s*mililitros?', 'ml'),
        (r'(\d+)\s*ml', 'ml'),
        # Porciones / unidades
        (r'(\d+)\s*porciones?', 'px'),
        (r'(\d+)\s*px', 'px'),
        (r'(\d+)\s*unidades?', 'und'),
        (r'(\d+)\s*und', 'und'),
    ]

    for patron, unidad in patrones:
        match = re.search(patron, text_lower)
        if match:
            valor = match.group(1).replace(',', '.')
            return {'valor': float(valor), 'unidad': unidad}

    return None

def extract_proveedor(text: str) -> str:
    patrones = [
        r'proveedor\s+(\w+)',
        r'de\s+(\w+)\s+proveedor',
    ]
    for patron in patrones:
        match = re.search(patron, text)
        if match:
            return match.group(1).capitalize()
    return None

def classify(text: str) -> dict:
    text_lower = text.lower().strip()
    detected_types = []

    for tipo, keywords in KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                detected_types.append(tipo)
                break

    es_novedad = 'novedad_calidad' in detected_types

    tipo_principal = None
    for tipo in detected_types:
        if tipo != 'novedad_calidad':
            tipo_principal = tipo
            break

    if not tipo_principal and es_novedad:
        tipo_principal = 'novedad_calidad'

    proveedor = extract_proveedor(text_lower)
    peso = extract_weight_from_text(text)

    return {
        'tipo': tipo_principal,
        'codigo_prefijo': RECORD_CODES.get(tipo_principal, 'REG'),
        'es_novedad': es_novedad,
        'proveedor': proveedor,
        'peso_texto': peso,
        'confianza': 'alta' if tipo_principal else 'baja'
    }
