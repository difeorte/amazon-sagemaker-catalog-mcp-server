"""Modelos de datos (dataclasses) para el MCP Server."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MemberInfo:
    """Miembro de un shape de tipo structure."""

    name: str
    shape_name: str
    documentation: str | None = None


@dataclass
class ShapeInfo:
    """Información de un shape del service model de botocore."""

    name: str
    shape_type: str  # structure, string, integer, boolean, list, map, timestamp, blob, long, float, double
    documentation: str | None = None
    members: dict[str, MemberInfo] | None = None  # Solo para structure
    required_members: list[str] | None = None  # Solo para structure
    member_shape: str | None = None  # Solo para list
    key_shape: str | None = None  # Solo para map
    value_shape: str | None = None  # Solo para map
    enum_values: list[str] | None = None  # Solo para string con enum


@dataclass
class OperationInfo:
    """Información de una operación del service model."""

    name: str  # PascalCase, ej: "ListDomains"
    documentation: str | None = None
    input_shape_name: str | None = None
    output_shape_name: str | None = None


@dataclass
class ServiceModel:
    """Representación intermedia del service model de botocore."""

    operations: dict[str, OperationInfo] = field(default_factory=dict)
    shapes: dict[str, ShapeInfo] = field(default_factory=dict)
    service_name: str = ""
    api_version: str = ""


@dataclass
class ToolDefinition:
    """Definición de una tool MCP generada desde una operación."""

    tool_name: str  # snake_case
    operation_name: str  # PascalCase original
    description: str
    input_schema: dict = field(default_factory=dict)
    required_params: list[str] = field(default_factory=list)
