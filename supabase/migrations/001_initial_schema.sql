create table if not exists customers (
    identification text primary key,
    full_name text not null,
    phone text not null,
    email text not null,
    customer_type text not null check (customer_type in ('nuevo', 'frecuente'))
);

create table if not exists products (
    sku text primary key,
    name text not null,
    category text not null,
    price numeric(14, 2) not null check (price >= 0),
    specifications text not null,
    tags text[] not null default '{}',
    warranty_months integer not null default 12 check (warranty_months >= 0)
);

create table if not exists orders (
    order_id text primary key,
    customer_identification text not null references customers(identification),
    status text not null,
    estimated_delivery date,
    address text not null
);

create table if not exists order_items (
    order_id text not null references orders(order_id) on delete cascade,
    product_sku text not null references products(sku),
    purchase_date date not null,
    primary key (order_id, product_sku)
);

create table if not exists warranty_tickets (
    ticket_id text primary key,
    customer_identification text not null references customers(identification),
    product_sku text not null references products(sku),
    reported_failure text not null,
    status text not null default 'Registrado - En Evaluación Técnica',
    created_at timestamptz not null default now()
);

create or replace function warranty_coverage(
    requested_identification text,
    requested_sku text
)
returns table (
    covered boolean,
    customer_identification text,
    product_sku text,
    purchase_date date,
    warranty_months integer,
    expires_at date,
    reason text
)
language sql
stable
as $$
    select
        (current_date <= (oi.purchase_date + make_interval(months => p.warranty_months))) as covered,
        o.customer_identification,
        oi.product_sku,
        oi.purchase_date,
        p.warranty_months,
        (oi.purchase_date + make_interval(months => p.warranty_months))::date as expires_at,
        case
            when current_date <= (oi.purchase_date + make_interval(months => p.warranty_months))
                then 'Cobertura vigente'
            else 'La cobertura venció'
        end as reason
    from order_items oi
    join orders o on o.order_id = oi.order_id
    join products p on p.sku = oi.product_sku
    where o.customer_identification = requested_identification
      and oi.product_sku = requested_sku
    order by oi.purchase_date desc
    limit 1;
$$;