import gspread
from google.oauth2.service_account import Credentials
import os
import pytz
from datetime import datetime

ECUADOR_TZ = pytz.timezone("America/Guayaquil")

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def get_sheet():
    creds = Credentials.from_service_account_file(
        os.getenv('GOOGLE_CREDENTIALS'),
        scopes=SCOPES
    )
    client = gspread.authorize(creds)
    return client.open_by_key(os.getenv('GOOGLE_SHEETS_ID'))

def append_bodega_record(record: dict, user_name: str) -> bool:
    try:
        sheet = get_sheet()
        worksheet = sheet.worksheet('Bodega')
        now = datetime.now(ECUADOR_TZ)
        fecha = now.strftime('%d/%m/%Y')
        hora = now.strftime('%H:%M')
        code = record.get('record_code', '')
        row = [
            code,
            fecha,
            hora,
            record.get('record_type', '').upper(),
            record.get('product', ''),
            str(record.get('weight_kg', '')) if record.get('weight_kg') else '',
            record.get('unit', ''),
            user_name,
            record.get('supplier_name', '') or '',
            record.get('location_name', '') or '',
            'OK',
            f'/foto {code}' if record.get('file_id') else 'Sin foto'
        ]
        worksheet.append_row(row)
        return True
    except Exception as e:
        print(f"Error append_bodega_record: {e}")
        return False
