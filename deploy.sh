#!/bin/bash
# ==========================================
# Deploy script — Bot Produccion Pepe Pez
# Uso: ./deploy.sh
# ==========================================
set -e

# Variables (ajustar según sea necesario)
PROJECT_DIR="/home/presidencia"
REPO_URL="https://github.com/alexcriolloraf/bot-produccion-ppez.git"

echo "=============================="
echo "  Deploy Bot Produccion"
echo "  $(date)"
echo "=============================="

# 1. Ir al directorio del proyecto
cd "$PROJECT_DIR"

# 2. Crear carpeta si no existe
if [ ! -d "bot-produccion-ppez" ]; then
    echo "[1/5] Clonando repositorio..."
    git clone "$REPO_URL"
    cd bot-produccion-ppez
else
    echo "[1/5] Actualizando repositorio..."
    cd bot-produccion-ppez
    git pull
fi

# 3. Restaurar .env si no existe
if [ ! -f ".env" ]; then
    echo "[2/5] Creando .env desde backup..."
    # Copiar .env anterior si existe
    if [ -f "$PROJECT_DIR/pepepez_bot/.env" ]; then
        cp "$PROJECT_DIR/pepepez_bot/.env" .
    elif [ -f "$PROJECT_DIR/bodega_bot/.env" ]; then
        cp "$PROJECT_DIR/bodega_bot/.env" .
    else
        echo "⚠️  No se encontro .env. Crea uno manualmente."
    fi
fi

# 4. Activar venv e instalar dependencias
echo "[3/5] Instalando dependencias..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt -q

# 5. Verificar que las migraciones esten corriendo
echo "[4/5] Verificando base de datos..."
# La base de datos deberia existir ya; aqui solo se verifica conexion
python3 -c "
from dotenv import load_dotenv
load_dotenv()
import os, psycopg2
try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    conn.close()
    print('  ✅ Conexion DB exitosa')
except Exception as e:
    print(f'  ⚠️  No se pudo conectar: {e}')
"

# 6. Copiar backups del proyecto anterior
echo "[5/5] Migrando datos anteriores..."
if [ -d "$PROJECT_DIR/pepepez_bot" ] && [ ! -d "backups" ]; then
    mkdir -p backups
    cp -r "$PROJECT_DIR/pepepez_bot/credentials.json" . 2>/dev/null || true
    echo "  ✅ Datos migrados"
fi

echo ""
echo "=============================="
echo "  Deploy completado!"
echo "  Para iniciar el bot:"
echo "    source venv/bin/activate"
echo "    cd pepepez_bot && python main.py"
echo "=============================="
