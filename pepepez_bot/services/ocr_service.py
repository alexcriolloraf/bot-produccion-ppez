import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import io
import re

def preprocess_image(image: Image.Image) -> Image.Image:
    """Preprocesa la imagen para mejorar lectura de displays digitales."""
    # Convertir a escala de grises
    image = image.convert('L')
    # Aumentar contraste
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(3.0)
    # Aumentar nitidez
    image = image.filter(ImageFilter.SHARPEN)
    # Escalar para mejor OCR
    width, height = image.size
    image = image.resize((width * 2, height * 2), Image.LANCZOS)
    return image

def extract_weight(image_bytes: bytes) -> dict:
    """
    Extrae el peso de una foto de balanza digital.
    Retorna: {'weight': 11.50, 'unit': 'kg', 'source': 'ocr'}
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
        processed = preprocess_image(image)

        # Configuración optimizada para números en displays
        config = '--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789.,'
        text = pytesseract.image_to_string(processed, config=config)

        # Buscar patrones de peso
        patrones = [
            r'(\d{1,3}[.,]\d{1,3})',  # formato 11.500 o 11,500
            r'(\d{1,4})',               # solo número entero
        ]

        for patron in patrones:
            matches = re.findall(patron, text)
            if matches:
                # Tomar el número más relevante
                for match in matches:
                    valor = float(match.replace(',', '.'))
                    # Filtrar valores razonables (0.1 a 999 kg)
                    if 0.1 <= valor <= 999:
                        return {
                            'weight': valor,
                            'unit': 'kg',
                            'source': 'ocr',
                            'confidence': 'high'
                        }

        return {'weight': None, 'source': 'ocr_failed', 'confidence': 'none'}

    except Exception as e:
        return {'weight': None, 'source': 'error', 'error': str(e)}
