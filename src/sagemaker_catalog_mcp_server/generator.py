"""Generador de tool definitions desde el service model de botocore."""

from __future__ import annotations

import re

from sagemaker_catalog_mcp_server.models import (
    OperationInfo,
    ServiceModel,
    ToolDefinition,
)
from sagemaker_catalog_mcp_server.utils.name_converter import NameConverter
from sagemaker_catalog_mcp_server.utils.type_converter import TypeConverter


# Regex para limpiar tags HTML de la documentación de botocore
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _clean_doc(doc: str | None) -> str:
    """Limpia tags HTML de la documentación de botocore."""
    if not doc:
        return "No description available."
    cleaned = _HTML_TAG_RE.sub("", doc).strip()
    return cleaned or "No description available."


class ToolGenerator:
    """Genera definiciones de tools MCP a partir del ServiceModel."""

    def __init__(self, service_model: ServiceModel):
        self.service_model = service_model
        self.type_converter = TypeConverter(service_model.shapes)

    def generate_all(self) -> list[ToolDefinition]:
        """Genera una ToolDefinition por cada operación del ServiceModel."""
        return [
            self.generate_tool(op)
            for op in self.service_model.operations.values()
        ]

    def generate_tool(self, operation: OperationInfo) -> ToolDefinition:
        """Genera una ToolDefinition para una operación específica."""
        tool_name = NameConverter.to_snake_case(operation.name)
        description = _clean_doc(operation.documentation)

        input_schema: dict = {"type": "object", "properties": {}}
        required_params: list[str] = []

        if operation.input_shape_name:
            schema = self.type_converter.to_json_schema(operation.input_shape_name)
            input_schema = schema
            required_params = schema.get("required", [])

        return ToolDefinition(
            tool_name=tool_name,
            operation_name=operation.name,
            description=description,
            input_schema=input_schema,
            required_params=required_params,
        )
