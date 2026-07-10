from database.connection import get_connection

def search_products(query: str) -> list[dict]:
    if not query or not query.strip():
        return []
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM products
                WHERE active = true
                AND (
                    name ILIKE %s
                    OR %s = ANY(aliases)
                )
                ORDER BY name
                LIMIT 5
            """, (f'%{query}%', query.lower().strip()))
            return cur.fetchall()

def get_product_by_name(name: str) -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM products
                WHERE active = true
                AND name ILIKE %s
                LIMIT 1
            """, (name.strip(),))
            return cur.fetchone()

def get_product_by_prefix(prefix: str) -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM products
                WHERE active = true AND prefix = %s
            """, (prefix.upper().strip(),))
            return cur.fetchone()

def create_product(name: str, prefix: str = None, aliases: list = None, unit: str = 'kg', min_kg: float = None, max_kg: float = None) -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO products (name, prefix, aliases, unit, min_kg, max_kg)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (name) DO UPDATE
                SET aliases = array_cat(products.aliases, %s),
                    active = true
                RETURNING *
            """, (name.strip(), prefix, aliases or [], unit, min_kg, max_kg, aliases or []))
            conn.commit()
            return cur.fetchone()

def get_or_create_product(name: str) -> dict:
    name = name.strip().lower()
    product = get_product_by_name(name)
    if product:
        return product
    product = search_products(name)
    if product:
        return product[0]
    return create_product(name.capitalize())
