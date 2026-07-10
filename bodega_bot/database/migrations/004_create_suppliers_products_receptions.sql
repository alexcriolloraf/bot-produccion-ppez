-- Migration 004: Crear tablas para recepcion de proveedores
-- Fecha: Julio 2026
-- Descripcion: Tablas para el nuevo flujo de bodega

-- 1. Catálogo de proveedores
CREATE TABLE IF NOT EXISTS suppliers (
    id            SERIAL PRIMARY KEY,
    code          VARCHAR(20) UNIQUE NOT NULL,
    name          VARCHAR(200) NOT NULL,
    aliases       TEXT[] DEFAULT '{}',
    contact_name  VARCHAR(100),
    phone         VARCHAR(20),
    active        BOOLEAN DEFAULT TRUE,
    created_by    BIGINT,
    created_at    TIMESTAMP DEFAULT NOW()
);

CREATE SEQUENCE IF NOT EXISTS suppliers_seq;

-- 2. Catálogo de productos (se alimenta con el tiempo)
CREATE TABLE IF NOT EXISTS products (
    id       SERIAL PRIMARY KEY,
    name     VARCHAR(100) NOT NULL UNIQUE,
    prefix   VARCHAR(5) NOT NULL UNIQUE,
    aliases  TEXT[] DEFAULT '{}',
    unit     VARCHAR(10) DEFAULT 'kg',
    min_kg   DECIMAL(8,3),
    max_kg   DECIMAL(8,3),
    active   BOOLEAN DEFAULT TRUE
);

-- 3. Recepción de proveedor (cabecera)
CREATE TABLE IF NOT EXISTS receptions (
    id                SERIAL PRIMARY KEY,
    reception_code    VARCHAR(20) UNIQUE NOT NULL,
    supplier_id       INTEGER REFERENCES suppliers(id),
    supplier_name     VARCHAR(200),
    status            VARCHAR(20) DEFAULT 'abierto',
    file_id           TEXT,
    created_by        BIGINT NOT NULL,
    closed_at         TIMESTAMP,
    created_at        TIMESTAMP DEFAULT NOW()
);

CREATE SEQUENCE IF NOT EXISTS receptions_seq;

-- 4. Items de la recepción
CREATE TABLE IF NOT EXISTS reception_items (
    id                SERIAL PRIMARY KEY,
    reception_id      INTEGER REFERENCES receptions(id) ON DELETE CASCADE,
    product_name      VARCHAR(150) NOT NULL,
    product_prefix    VARCHAR(5),
    weight_kg         DECIMAL(8,3),
    unit              VARCHAR(10) DEFAULT 'kg',
    status            VARCHAR(20) DEFAULT 'pendiente',
    lot_code          VARCHAR(30) UNIQUE NOT NULL,
    supplier_lot      VARCHAR(30),
    weighed_by        BIGINT,
    weighed_at        TIMESTAMP,
    created_at        TIMESTAMP DEFAULT NOW()
);

CREATE SEQUENCE IF NOT EXISTS reception_items_seq;

-- 5. Índices para búsqueda
CREATE INDEX IF NOT EXISTS idx_suppliers_active ON suppliers (active);
CREATE INDEX IF NOT EXISTS idx_receptions_status ON receptions (status);
CREATE INDEX IF NOT EXISTS idx_reception_items_status ON reception_items (status);
CREATE INDEX IF NOT EXISTS idx_reception_items_lot ON reception_items (lot_code);
CREATE INDEX IF NOT EXISTS idx_reception_items_reception ON reception_items (reception_id);
