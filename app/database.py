"""Estructuras de datos simular base de datos en memoria (Mock Data)."""

DB_CLIENTES = {
    "10101010": {
        "nombre": "Liceth Guerrero",
        "telefono": "3001234567",
        "correo": "liceth@example.com",
        "tipo": "frecuente",
    }
}

DB_PRODUCTOS = [
    {
        "sku": "LAP-DG-01",
        "nombre": "Laptop Pro Art 16",
        "categoria": "computadores",
        "precio": 4800000,
        "especificaciones": "AMD Ryzen 9, 32GB RAM, SSD 1TB, Nvidia RTX 4060, Pantalla OLED 100% DCI-P3",
        "tags": ["diseño gráfico", "edición de video", "render"],
    },
    {
        "sku": "LAP-OFF-02",
        "nombre": "Laptop Slim Business",
        "categoria": "computadores",
        "precio": 2500000,
        "especificaciones": "Intel i5, 16GB RAM, SSD 512GB, Gráficos Integrados",
        "tags": ["oficina", "estudio", "trabajo"],
    },
    {
        "sku": "TV-OLED-55",
        "nombre": "Smart TV OLED 55 4K",
        "categoria": "televisores",
        "precio": 3900000,
        "especificaciones": "55 pulgadas, 120Hz, HDMI 2.1, HDR10+, Dolby Atmos",
        "tags": ["cinema", "gaming"],
    },
    {
        "sku": "CEL-PRO-MAX",
        "nombre": "Smartphone Ultra Cam 5G",
        "categoria": "celulares",
        "precio": 4200000,
        "especificaciones": "256GB, Cámara 200MP, Pantalla AMOLED 120Hz, Batería 5000mAh",
        "tags": ["fotografía", "premium"],
    },
]

DB_PEDIDOS = {
    "PED-1001": {
        "identificacion_cliente": "10101010",
        "estado": "En camino a centro de distribución",
        "fecha_estimada": "2026-09-25",
        "direccion": "Calle 10 # 40-20, Medellín",
        "items": ["LAP-DG-01"],
    },
    "PED-1002": {
        "identificacion_cliente": "10101010",
        "estado": "Entregado",
        "fecha_estimada": "2026-02-01",
        "direccion": "Calle 10 # 40-20, Medellín",
        "items": ["TV-OLED-55"],
    },
}

DB_GARANTIAS = {}
DB_CHAT_SESSIONS = {}
DB_CHAT_MESSAGES = []
