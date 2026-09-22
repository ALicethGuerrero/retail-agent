"""Esquemas de validación Pydantic para datos de cliente y estado de sesión."""

import re
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class ValidarClienteNuevoInput(BaseModel):
    """Representar los datos de registro de un cliente nuevo."""

    identificacion: str = Field(
        ..., description="Número de identificación de 4 a 11 dígitos numéricos."
    )
    nombre_completo: str = Field(
        ..., description="Nombre completo con letras, espacios, tildes y ñ."
    )
    telefono: str = Field(..., description="Número de 10 dígitos que inicia en 3 o 6.")
    correo: EmailStr = Field(..., description="Correo electrónico válido.")

    @field_validator("identificacion")
    @classmethod
    def validar_identificacion(cls, value: str) -> str:
        """Validar que la identificación tenga entre 4 y 11 dígitos numéricos."""
        value = value.strip()
        if not re.fullmatch(r"\d{4,11}", value):
            raise ValueError("La identificación debe contener entre 4 y 11 dígitos.")
        return value

    @field_validator("nombre_completo")
    @classmethod
    def validar_nombre(cls, value: str) -> str:
        """Validar que el nombre contenga entre 1 y 100 caracteres y solo letras/espacios."""
        value = value.strip()
        if not 1 <= len(value) <= 100:
            raise ValueError("El nombre debe tener entre 1 y 100 caracteres.")
        if not re.fullmatch(r"[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+", value):
            raise ValueError("El nombre solo admite letras y espacios.")
        return value

    @field_validator("telefono")
    @classmethod
    def validar_telefono(cls, value: str) -> str:
        """Validar que el teléfono tenga 10 dígitos e inicie por 3 o 6."""
        value = value.strip()
        if not re.fullmatch(r"[36]\d{9}", value):
            raise ValueError("El teléfono debe tener 10 dígitos e iniciar en 3 o 6.")
        return value


class SessionState(BaseModel):
    """Representar el contexto conservado durante una conversación."""

    cliente_identificacion: Optional[str] = None
    cliente_nombre: Optional[str] = None
    tipo_cliente: Optional[str] = None
    productos_consultados: list[str] = Field(default_factory=list)
    presupuesto_mencionado: Optional[float] = None
    ultimo_pedido_consultado: Optional[str] = None
    preferencias_usuario: list[str] = Field(default_factory=list)
