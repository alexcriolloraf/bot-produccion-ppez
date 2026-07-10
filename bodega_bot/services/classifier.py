import re

KEYWORDS = {
    'apertura': ['apertura', 'abriendo', 'abrimos'],
    'cierre': ['cierre', 'cerrando', 'cerramos'],
    'ingreso': [
        'ingresa', 'ingresan', 'ingreso', 'llego', 'llegó',
        'recibido', 'entrada de', 'ingresaron'
    ],
    'despacho': [
        'despacho', 'despachado', 'sale para', 'sale a',
        'enviado a', 'entrega a', 'despachar'
    ],
    'devolucion': [
        'devolucion', 'devolución', 'se devuelve', 'regresa',
        'se da de baja', 'baja'
    ],
    'inventario': [
        'inventario', 'stock', 'quedan', 'hay en bodega',
        'conteo', 'recuento'
    ],
    'novedad': [
        'novedad', 'problema', 'dañado', 'mal estado',
        'vencido', 'contaminado', 'pelos', 'cabellos'
    ],
    'mantenimiento': [
        'mantenimiento', 'dañado', 'no funciona',
        'roto', 'falla', 'revisar'
    ],
    'requerimiento': [
        'requerimiento', 'pedido', 'solicitud', 'requiere'
    ],
}

REQUIERE_DESTINO = ['despacho']
REQUIERE_PROVEEDOR = ['ingreso']
REQUIERE_PESO = ['ingreso', 'despacho', 'devolucion', 'inventario']

def classify(text: str) -> dict:
    text_lower = text.lower().strip()
    tipo = None

    for t, keywords in KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                tipo = t
                break
        if tipo:
            break

    proveedor = extract_proveedor(text_lower)
    peso = extract_weight_from_text(text)
    destino = extract_destino(text_lower)

    return {
        'tipo': tipo,
        'proveedor': proveedor,
        'peso_texto': peso,
        'destino': destino,
        'requiere_destino': tipo in REQUIERE_DESTINO,
        'requiere_proveedor': tipo in REQUIERE_PROVEEDOR,
        'requiere_peso': tipo in REQUIERE_PESO,
        'confianza': 'alta' if tipo else 'baja'
    }

def extract_proveedor(text: str) -> str:
    patrones = [
        r'proveedor\s+(\w+)',
        r'de\s+(\w+)\s+proveedor',
        r'pronaca|la\s+fabril|agripac|distrib\w+',
    ]
    for patron in patrones:
        match = re.search(patron, text)
        if match:
            return match.group(0).capitalize()
    return None

def extract_destino(text: str) -> str:
    locales = {
        'mall del sol': 'Mall del Sol',
        'mall': 'Mall del Sol',
        'san marino': 'San Marino',
        'marino': 'San Marino',
        'batan': 'Plaza Batán',
        'batán': 'Plaza Batán',
        'village': 'Village Plaza',
        'puerto': 'Puerto Santa Ana',
        'santa ana': 'Puerto Santa Ana',
        'portela': 'Isla Portela',
        'isla': 'Isla Portela',
        'ceibos': 'Ceibos',
        'produccion': 'Producción',
        'producción': 'Producción',
    }
    for key, value in locales.items():
        if key in text:
            return value
    return None

def extract_weight_from_text(text: str) -> dict:
    text_lower = text.lower().strip()
    patrones = [
        (r'(\d+[\.,]\d+)\s*kilogramos?', 'kg'),
        (r'(\d+[\.,]\d+)\s*kg', 'kg'),
        (r'(\d+)\s*kilogramos?', 'kg'),
        (r'(\d+)\s*kg', 'kg'),
        (r'(\d+[\.,]\d+)\s*gramos?', 'gr'),
        (r'(\d+[\.,]\d+)\s*grs?', 'gr'),
        (r'(\d+)\s*gramos?', 'gr'),
        (r'(\d+)\s*grs?', 'gr'),
        (r'(\d+[\.,]\d+)\s*libras?', 'lb'),
        (r'(\d+[\.,]\d+)\s*lbs?', 'lb'),
        (r'(\d+)\s*libras?', 'lb'),
        (r'(\d+)\s*lbs?', 'lb'),
        (r'(\d+[\.,]\d+)\s*litros?', 'lt'),
        (r'(\d+[\.,]\d+)\s*lts?', 'lt'),
        (r'(\d+)\s*litros?', 'lt'),
        (r'(\d+)\s*lts?', 'lt'),
        (r'(\d+)\s*ml', 'ml'),
        (r'(\d+)\s*unidades?', 'und'),
        (r'(\d+)\s*und', 'und'),
        (r'(\d+)\s*cajas?', 'caja'),
        (r'(\d+)\s*fundas?', 'funda'),
    ]
    for patron, unidad in patrones:
        match = re.search(patron, text_lower)
        if match:
            valor = match.group(1).replace(',', '.')
            return {'valor': float(valor), 'unidad': unidad}
    return None
