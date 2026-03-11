"""Executor de operaciones contra AWS DataZone via boto3."""

from __future__ import annotations

import base64
import json
import logging
import sys
from datetime import datetime
from decimal import Decimal
from typing import Any

import boto3
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    EndpointConnectionError,
    NoCredentialsError,
    PartialCredentialsError,
)

logger = logging.getLogger(__name__)


class ToolExecutionError(Exception):
    """Error durante la ejecución de una tool."""

    def __init__(self, message: str, error_code: str = "ExecutionError", operation: str = ""):
        self.message = message
        self.error_code = error_code
        self.operation = operation
        super().__init__(message)


class ToolExecutor:
    """Ejecuta operaciones de DataZone contra AWS usando boto3."""

    def __init__(self, region: str | None = None, profile: str | None = None):
        self.client = self._create_client(region, profile)

    def _create_client(self, region: str | None, profile: str | None):
        """Crea el cliente boto3 de DataZone."""
        session_kwargs: dict[str, Any] = {}
        if profile:
            session_kwargs["profile_name"] = profile
        if region:
            session_kwargs["region_name"] = region

        session = boto3.Session(**session_kwargs)
        return session.client("datazone")

    def execute(self, operation_name: str, parameters: dict) -> dict:
        """Ejecuta una operación de DataZone y retorna el resultado serializado.

        Args:
            operation_name: Nombre de la operación, puede ser PascalCase o snake_case.
            parameters: Diccionario de parámetros para la operación.

        Returns:
            Respuesta serializada como dict JSON-compatible.

        Raises:
            ToolExecutionError: Si la operación falla.
        """
        # Si viene en snake_case, convertir a PascalCase primero
        if "_" in operation_name:
            from sagemaker_catalog_mcp_server.utils.name_converter import NameConverter
            operation_name = NameConverter.to_pascal_case(operation_name)

        # Convertir PascalCase a snake_case para el método de boto3
        method_name = self._to_boto3_method(operation_name)

        try:
            method = getattr(self.client, method_name)
        except AttributeError:
            raise ToolExecutionError(
                message=f"Operación no soportada: {operation_name} (método {method_name})",
                error_code="UnsupportedOperation",
                operation=operation_name,
            )

        try:
            response = method(**parameters)
            return self._serialize_response(response)
        except ClientError as e:
            error_info = e.response.get("Error", {})
            raise ToolExecutionError(
                message=f"{error_info.get('Message', str(e))}",
                error_code=error_info.get("Code", "UnknownError"),
                operation=operation_name,
            )
        except (NoCredentialsError, PartialCredentialsError) as e:
            raise ToolExecutionError(
                message=f"Credenciales AWS no configuradas o incompletas: {e}",
                error_code="CredentialsError",
                operation=operation_name,
            )
        except EndpointConnectionError as e:
            raise ToolExecutionError(
                message=f"No se pudo conectar al endpoint de AWS: {e}",
                error_code="ConnectionError",
                operation=operation_name,
            )
        except BotoCoreError as e:
            raise ToolExecutionError(
                message=f"Error de AWS: {e}",
                error_code="AWSError",
                operation=operation_name,
            )

    def _to_boto3_method(self, operation_name: str) -> str:
        """Convierte PascalCase a snake_case para métodos de boto3."""
        import re
        return re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "_", operation_name).lower()

    def _serialize_response(self, response: dict) -> dict:
        """Serializa la respuesta de boto3 a tipos JSON-compatibles."""
        # Eliminar ResponseMetadata
        result = {k: v for k, v in response.items() if k != "ResponseMetadata"}
        return self._serialize_value(result)

    def _serialize_value(self, value: Any) -> Any:
        """Serializa un valor individual recursivamente."""
        if isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, bytes):
            return base64.b64encode(value).decode("utf-8")
        elif isinstance(value, Decimal):
            if value == int(value):
                return int(value)
            return float(value)
        elif isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._serialize_value(item) for item in value]
        elif isinstance(value, set):
            return [self._serialize_value(item) for item in sorted(value)]
        return value
