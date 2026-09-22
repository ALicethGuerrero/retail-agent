insert into customers (identification, full_name, phone, email, customer_type)
values ('10101010', 'Liceth Guerrero', '3001234567', 'liceth@example.com', 'frecuente')
on conflict (identification) do nothing;

insert into products (sku, name, category, price, specifications, tags, warranty_months)
values
    ('LAP-DG-01', 'Laptop Pro Art 16', 'computadores', 4800000, 'AMD Ryzen 9, 32GB RAM, SSD 1TB, Nvidia RTX 4060, Pantalla OLED 100% DCI-P3', array['diseño gráfico', 'edición de video', 'render'], 12),
    ('LAP-OFF-02', 'Laptop Slim Business', 'computadores', 2500000, 'Intel i5, 16GB RAM, SSD 512GB, Gráficos Integrados', array['oficina', 'estudio', 'trabajo'], 12),
    ('TV-OLED-55', 'Smart TV OLED 55 4K', 'televisores', 3900000, '55 pulgadas, 120Hz, HDMI 2.1, HDR10+, Dolby Atmos', array['cinema', 'gaming'], 12),
    ('CEL-PRO-MAX', 'Smartphone Ultra Cam 5G', 'celulares', 4200000, '256GB, Cámara 200MP, Pantalla AMOLED 120Hz, Batería 5000mAh', array['fotografía', 'premium'], 12)
on conflict (sku) do nothing;

insert into orders (order_id, customer_identification, status, estimated_delivery, address)
values
    ('PED-1001', '10101010', 'En camino a centro de distribución', '2026-09-25', 'Calle 10 # 40-20, Medellín'),
    ('PED-1002', '10101010', 'Entregado', '2026-02-01', 'Calle 10 # 40-20, Medellín')
on conflict (order_id) do nothing;

insert into order_items (order_id, product_sku, purchase_date)
values
    ('PED-1001', 'LAP-DG-01', '2026-01-15'),
    ('PED-1002', 'TV-OLED-55', '2026-01-15')
on conflict (order_id, product_sku) do nothing;