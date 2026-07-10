import gspread
from google.oauth2.service_account import Credentials
import os
from datetime import datetime

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

def init_headers():
    try:
        sheet = get_sheet()
        worksheet = sheet.sheet1
        worksheet.update_title('Registros')
        first_row = worksheet.row_values(1)
        if not first_row:
            headers = [
                'Codigo', 'Fecha', 'Hora', 'Tipo',
                'Descripcion', 'Peso', 'Unidad',
                'Colaborador', 'Proveedor', 'Estado', 'Ver Foto'
            ]
            worksheet.append_row(headers)
            worksheet.format('A1:K1', {
                'backgroundColor': {'red': 0.0, 'green': 0.47, 'blue': 0.44},
                'textFormat': {
                    'bold': True,
                    'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}
                },
                'horizontalAlignment': 'CENTER'
            })
        return True
    except Exception as e:
        print(f"Error init_headers: {e}")
        return False

def append_record(record: dict, user_name: str) -> bool:
    try:
        sheet = get_sheet()
        worksheet = sheet.sheet1
        fecha = datetime.now().strftime('%d/%m/%Y')
        hora = datetime.now().strftime('%H:%M')

        code = record.get('record_code', '')
        tiene_foto = 'Si' if record.get('file_id') else 'No'

        row = [
            code,
            fecha,
            hora,
            record.get('record_type', '').upper(),
            record.get('product', ''),
            str(record.get('weight_kg', '')) if record.get('weight_kg') else '',
            record.get('unit', ''),
            user_name,
            record.get('supplier', '') or '',
            'OK',
            f'/foto {code}' if tiene_foto == 'Si' else 'Sin foto'
        ]
        worksheet.append_row(row)
        return True
    except Exception as e:
        print(f"Error append_record: {e}")
        return False

def append_ticket(ticket: dict, user_name: str) -> bool:
    try:
        sheet = get_sheet()
        try:
            worksheet = sheet.worksheet('Tickets')
        except:
            worksheet = sheet.add_worksheet('Tickets', rows=1000, cols=10)
            headers = [
                'Ticket', 'Fecha', 'Hora', 'Tipo',
                'Descripcion', 'Reportado por', 'Proveedor', 'Estado'
            ]
            worksheet.append_row(headers)
            worksheet.format('A1:H1', {
                'backgroundColor': {'red': 0.8, 'green': 0.0, 'blue': 0.0},
                'textFormat': {
                    'bold': True,
                    'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}
                },
                'horizontalAlignment': 'CENTER'
            })
        fecha = datetime.now().strftime('%d/%m/%Y')
        hora = datetime.now().strftime('%H:%M')
        row = [
            ticket.get('ticket_code', ''),
            fecha,
            hora,
            ticket.get('ticket_type', '').upper(),
            ticket.get('description', ''),
            user_name,
            ticket.get('supplier', '') or '',
            'ABIERTO'
        ]
        worksheet.append_row(row)
        return True
    except Exception as e:
        print(f"Error append_ticket: {e}")
        return False
