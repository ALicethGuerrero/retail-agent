import os
from datetime import date
from typing import Any, Protocol

from sqlalchemy import text

from app.database import DB_CLIENTES, DB_GARANTIAS, DB_PEDIDOS, DB_PRODUCTOS
from app.db.postgres import get_engine, use_mock_data


class RetailRepository(Protocol):
    """Definir las operaciones de acceso a datos para las tools."""

    def find_customer(self, identification: str) -> dict[str, Any] | None: ...
    def create_customer(self, data: dict[str, Any]) -> dict[str, Any]: ...
    def list_products(self, filters: dict[str, Any]) -> list[dict[str, Any]]: ...
    def compare_products(self, skus: list[str]) -> list[dict[str, Any]]: ...
    def find_orders(self, order_id: str | None, identification: str | None) -> list[dict[str, Any]]: ...
    def update_order_address(self, order_id: str, address: str) -> bool: ...
    def get_coverage(self, identification: str, sku: str) -> dict[str, Any] | None: ...
    def list_warranty_tickets(self, identification: str, sku: str) -> list[dict[str, Any]]: ...
    def create_warranty_ticket(self, data: dict[str, Any]) -> dict[str, Any]: ...


class MockRetailRepository:
    """Proporcionar una implementación local para pruebas sin PostgreSQL."""

    def find_customer(self, identification: str) -> dict[str, Any] | None:
        customer = DB_CLIENTES.get(identification)
        if not customer:
            return None
        return {
            "identification": identification,
            "full_name": customer["nombre"],
            "phone": customer["telefono"],
            "email": customer["correo"],
            "customer_type": customer["tipo"],
        }

    def create_customer(self, data: dict[str, Any]) -> dict[str, Any]:
        DB_CLIENTES[data["identification"]] = {
            "nombre": data["full_name"],
            "telefono": data["phone"],
            "correo": data["email"],
            "tipo": data["customer_type"],
        }
        return self.find_customer(data["identification"]) or {}

    def list_products(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        products = DB_PRODUCTOS
        if filters.get("category"):
            products = [p for p in products if p["categoria"] == filters["category"]]
        if filters.get("budget") is not None:
            products = [p for p in products if p["precio"] <= filters["budget"]]
        if filters.get("use"):
            requested_use = filters["use"].lower()
            products = [
                p for p in products
                if any(tag in requested_use for tag in p["tags"])
                or requested_use in p["especificaciones"].lower()
            ]
        return [self._product(p) for p in products]

    def compare_products(self, skus: list[str]) -> list[dict[str, Any]]:
        return [self._product(p) for p in DB_PRODUCTOS if p["sku"] in skus]

    def find_orders(self, order_id: str | None, identification: str | None) -> list[dict[str, Any]]:
        orders = DB_PEDIDOS
        if order_id:
            orders = {order_id: orders[order_id]} if order_id in orders else {}
        elif identification:
            orders = {key: value for key, value in orders.items() if value["identificacion_cliente"] == identification}
        return [{"order_id": key, **self._order(value)} for key, value in orders.items()]

    def update_order_address(self, order_id: str, address: str) -> bool:
        if order_id not in DB_PEDIDOS:
            return False
        DB_PEDIDOS[order_id]["direccion"] = address
        return True

    def get_coverage(self, identification: str, sku: str) -> dict[str, Any] | None:
        order = next(
            (value for value in DB_PEDIDOS.values()
             if value["identificacion_cliente"] == identification and sku in value["items"]),
            None,
        )
        product = next((value for value in DB_PRODUCTOS if value["sku"] == sku), None)
        if not order or not product:
            return None
        purchase_date = date(2026, 1, 15)
        expires_at = self._add_months(purchase_date, product.get("warranty_months", 12))
        covered = date.today() <= expires_at
        return {
            "covered": covered,
            "customer_identification": identification,
            "product_sku": sku,
            "purchase_date": purchase_date.isoformat(),
            "warranty_months": 12,
            "expires_at": expires_at.isoformat(),
            "reason": "Cobertura vigente" if covered else "La cobertura venció",
        }

    def list_warranty_tickets(self, identification: str, sku: str) -> list[dict[str, Any]]:
        return [
            {"ticket_id": ticket_id, **ticket}
            for ticket_id, ticket in DB_GARANTIAS.items()
            if ticket["identificacion_cliente"] == identification and ticket["sku"] == sku
        ]

    def create_warranty_ticket(self, data: dict[str, Any]) -> dict[str, Any]:
        ticket_id = f"TK-{len(DB_GARANTIAS) + 8001}"
        DB_GARANTIAS[ticket_id] = {
            "identificacion_cliente": data["customer_identification"],
            "sku": data["product_sku"],
            "falla": data["reported_failure"],
            "estado": "Registrado - En Evaluación Técnica",
        }
        return {"ticket_id": ticket_id, **DB_GARANTIAS[ticket_id]}

    @staticmethod
    def _product(product: dict[str, Any]) -> dict[str, Any]:
        return {
            "sku": product["sku"],
            "name": product["nombre"],
            "category": product["categoria"],
            "price": product["precio"],
            "specifications": product["especificaciones"],
            "tags": product["tags"],
            "warranty_months": product.get("warranty_months", 12),
        }

    @staticmethod
    def _order(order: dict[str, Any]) -> dict[str, Any]:
        return {
            "customer_identification": order["identificacion_cliente"],
            "status": order["estado"],
            "estimated_delivery": order["fecha_estimada"],
            "address": order["direccion"],
            "items": order["items"],
        }

    @staticmethod
    def _add_months(start: date, months: int) -> date:
        month_index = start.month - 1 + months
        year = start.year + month_index // 12
        month = month_index % 12 + 1
        return date(year, month, min(start.day, 28))


class PostgresRetailRepository:
    """Ejecutar las operaciones de retail contra PostgreSQL."""

    def __init__(self) -> None:
        self.engine = get_engine()

    def find_customer(self, identification: str) -> dict[str, Any] | None:
        query = text("select * from customers where identification = :identification")
        with self.engine.connect() as connection:
            row = connection.execute(query, {"identification": identification}).mappings().first()
        return dict(row) if row else None

    def create_customer(self, data: dict[str, Any]) -> dict[str, Any]:
        query = text("""
            insert into customers (identification, full_name, phone, email, customer_type)
            values (:identification, :full_name, :phone, :email, :customer_type)
            returning *
        """)
        with self.engine.begin() as connection:
            row = connection.execute(query, data).mappings().one()
        return dict(row)

    def list_products(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        conditions = []
        parameters: dict[str, Any] = {}
        if filters.get("category"):
            conditions.append("category = :category")
            parameters["category"] = filters["category"]
        if filters.get("budget") is not None:
            conditions.append("price <= :budget")
            parameters["budget"] = filters["budget"]
        where = f" where {' and '.join(conditions)}" if conditions else ""
        query = text(f"select * from products{where}")
        with self.engine.connect() as connection:
            products = [dict(row) for row in connection.execute(query, parameters).mappings()]
        if filters.get("use"):
            requested_use = filters["use"].lower()
            products = [
                product for product in products
                if any(tag.lower() in requested_use for tag in product.get("tags", []))
                or requested_use in product["specifications"].lower()
            ]
        return products

    def compare_products(self, skus: list[str]) -> list[dict[str, Any]]:
        query = text("select * from products where sku = any(:skus)")
        with self.engine.connect() as connection:
            return [dict(row) for row in connection.execute(query, {"skus": skus}).mappings()]

    def find_orders(self, order_id: str | None, identification: str | None) -> list[dict[str, Any]]:
        conditions = []
        parameters: dict[str, Any] = {}
        if order_id:
            conditions.append("o.order_id = :order_id")
            parameters["order_id"] = order_id
        elif identification:
            conditions.append("o.customer_identification = :identification")
            parameters["identification"] = identification
        where = f" where {' and '.join(conditions)}" if conditions else ""
        query = text(f"""
            select o.*, coalesce(
                json_agg(oi.product_sku) filter (where oi.product_sku is not null),
                '[]'::json
            ) as items
            from orders o
            left join order_items oi on oi.order_id = o.order_id
            {where}
            group by o.order_id
        """)
        with self.engine.connect() as connection:
            rows = connection.execute(query, parameters).mappings()
            return [
                {
                    "order_id": row["order_id"],
                    "customer_identification": row["customer_identification"],
                    "status": row["status"],
                    "estimated_delivery": row["estimated_delivery"].isoformat() if row["estimated_delivery"] else None,
                    "address": row["address"],
                    "items": row["items"],
                }
                for row in rows
            ]

    def update_order_address(self, order_id: str, address: str) -> bool:
        query = text("update orders set address = :address where order_id = :order_id")
        with self.engine.begin() as connection:
            result = connection.execute(query, {"address": address, "order_id": order_id})
        return result.rowcount > 0

    def get_coverage(self, identification: str, sku: str) -> dict[str, Any] | None:
        query = text("select * from warranty_coverage(:identification, :sku)")
        with self.engine.connect() as connection:
            row = connection.execute(query, {"identification": identification, "sku": sku}).mappings().first()
        return dict(row) if row else None

    def list_warranty_tickets(self, identification: str, sku: str) -> list[dict[str, Any]]:
        query = text("""
            select * from warranty_tickets
            where customer_identification = :identification and product_sku = :sku
            order by created_at desc
        """)
        with self.engine.connect() as connection:
            return [dict(row) for row in connection.execute(query, {"identification": identification, "sku": sku}).mappings()]

    def create_warranty_ticket(self, data: dict[str, Any]) -> dict[str, Any]:
        query = text("""
            with next_ticket as (
                select coalesce(max(substring(ticket_id from 4)::integer), 8000) + 1 as number
                from warranty_tickets
            )
            insert into warranty_tickets (ticket_id, customer_identification, product_sku, reported_failure)
            select 'TK-' || number, :customer_identification, :product_sku, :reported_failure
            from next_ticket
            returning *
        """)
        with self.engine.begin() as connection:
            row = connection.execute(query, data).mappings().one()
        return dict(row)


def get_repository() -> RetailRepository:
    """Seleccionar el repositorio mock o PostgreSQL según el entorno."""
    if use_mock_data():
        return MockRetailRepository()
    if not os.getenv("DATABASE_URL"):
        raise RuntimeError("Configura DATABASE_URL para usar PostgreSQL.")
    return PostgresRetailRepository()