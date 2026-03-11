"""Conversión de tipos botocore a JSON Schema."""

from __future__ import annotations

from sagemaker_catalog_mcp_server.models import ShapeInfo

# Mapeo de tipos primitivos de botocore a JSON Schema
_PRIMITIVE_MAP: dict[str, dict] = {
    "string": {"type": "string"},
    "integer": {"type": "integer"},
    "long": {"type": "integer"},
    "float": {"type": "number"},
    "double": {"type": "number"},
    "boolean": {"type": "boolean"},
    "timestamp": {"type": "string", "format": "date-time"},
    "blob": {"type": "string", "format": "base64"},
}


class TypeConverter:
    """Convierte shapes de botocore a JSON Schema, resolviendo recursivamente."""

    def __init__(self, shapes: dict[str, ShapeInfo]):
        self.shapes = shapes
        self._resolving: set[str] = set()

    def to_json_schema(self, shape_name: str) -> dict:
        """Convierte un shape de botocore a JSON Schema."""
        if shape_name not in self.shapes:
            return {"type": "object"}

        if shape_name in self._resolving:
            # Ciclo detectado — retornar object genérico para evitar recursión infinita
            return {"type": "object", "description": f"Circular reference to {shape_name}"}

        self._resolving.add(shape_name)
        try:
            shape = self.shapes[shape_name]
            return self._convert(shape)
        finally:
            self._resolving.discard(shape_name)

    def _convert(self, shape: ShapeInfo) -> dict:
        """Convierte un shape según su tipo."""
        if shape.shape_type == "structure":
            return self._convert_structure(shape)
        elif shape.shape_type == "list":
            return self._convert_list(shape)
        elif shape.shape_type == "map":
            return self._convert_map(shape)
        else:
            return self._convert_primitive(shape)

    def _convert_primitive(self, shape: ShapeInfo) -> dict:
        """Convierte tipos primitivos."""
        schema = dict(_PRIMITIVE_MAP.get(shape.shape_type, {"type": "string"}))
        if shape.enum_values:
            schema["enum"] = shape.enum_values
        if shape.documentation:
            schema["description"] = shape.documentation
        return schema

    def _convert_structure(self, shape: ShapeInfo) -> dict:
        """Convierte structure a JSON Schema object."""
        schema: dict = {"type": "object"}
        if shape.documentation:
            schema["description"] = shape.documentation

        if shape.members:
            properties = {}
            for member_name, member_info in shape.members.items():
                prop = self.to_json_schema(member_info.shape_name)
                if member_info.documentation:
                    prop["description"] = member_info.documentation
                properties[member_name] = prop
            schema["properties"] = properties

        if shape.required_members:
            schema["required"] = shape.required_members

        return schema

    def _convert_list(self, shape: ShapeInfo) -> dict:
        """Convierte list a JSON Schema array."""
        schema: dict = {"type": "array"}
        if shape.documentation:
            schema["description"] = shape.documentation
        if shape.member_shape:
            schema["items"] = self.to_json_schema(shape.member_shape)
        return schema

    def _convert_map(self, shape: ShapeInfo) -> dict:
        """Convierte map a JSON Schema object con additionalProperties."""
        schema: dict = {"type": "object"}
        if shape.documentation:
            schema["description"] = shape.documentation
        if shape.value_shape:
            schema["additionalProperties"] = self.to_json_schema(shape.value_shape)
        return schema
