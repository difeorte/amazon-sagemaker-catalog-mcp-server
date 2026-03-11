"""Parser del service model de botocore."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import botocore

from sagemaker_catalog_mcp_server.models import (
    MemberInfo,
    OperationInfo,
    ServiceModel,
    ShapeInfo,
)


class ServiceModelNotFoundError(Exception):
    """El archivo service-2.json no se encontró en botocore."""


class ServiceModelParseError(Exception):
    """Error al parsear el service model."""


class ServiceModelParser:
    """Lee y parsea el service model de DataZone desde botocore."""

    def __init__(self, service_name: str = "datazone"):
        self.SERVICE_NAME = service_name

    def find_service_model_path(self) -> str:
        """Localiza el service-2.json del servicio en el paquete botocore instalado."""
        botocore_dir = Path(botocore.__file__).parent
        data_dir = botocore_dir / "data" / self.SERVICE_NAME

        if not data_dir.exists():
            raise ServiceModelNotFoundError(
                f"Directorio del servicio no encontrado: {data_dir}. "
                f"botocore version: {botocore.__version__}"
            )

        # Buscar la versión más reciente del API
        versions = sorted(
            [d.name for d in data_dir.iterdir() if d.is_dir()], reverse=True
        )
        if not versions:
            raise ServiceModelNotFoundError(
                f"No se encontraron versiones del API en: {data_dir}. "
                f"botocore version: {botocore.__version__}"
            )

        # Buscar service-2.json o service-2.json.gz
        version_dir = data_dir / versions[0]
        for filename in ("service-2.json", "service-2.json.gz"):
            candidate = version_dir / filename
            if candidate.exists():
                return str(candidate)

        raise ServiceModelNotFoundError(
            f"service-2.json no encontrado en: {version_dir}. "
            f"botocore version: {botocore.__version__}"
        )

    def parse(self, service_model_path: str | None = None) -> ServiceModel:
        """Lee y parsea el service-2.json.

        Args:
            service_model_path: Ruta al archivo. Si es None, lo busca en botocore.

        Returns:
            ServiceModel con operaciones y shapes parseados.
        """
        if service_model_path is None:
            service_model_path = self.find_service_model_path()

        try:
            if service_model_path.endswith(".gz"):
                with gzip.open(service_model_path, "rt", encoding="utf-8") as f:
                    raw = json.load(f)
            else:
                with open(service_model_path) as f:
                    raw = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            raise ServiceModelParseError(f"Error leyendo {service_model_path}: {e}")

        return self._parse_raw(raw)

    def parse_from_dict(self, raw: dict) -> ServiceModel:
        """Parsea un service model desde un diccionario (útil para testing)."""
        return self._parse_raw(raw)

    def _parse_raw(self, raw: dict) -> ServiceModel:
        """Parsea el JSON crudo del service model."""
        metadata = raw.get("metadata", {})

        operations = {}
        for op_name, op_data in raw.get("operations", {}).items():
            operations[op_name] = self._parse_operation(op_name, op_data)

        shapes = {}
        for shape_name, shape_data in raw.get("shapes", {}).items():
            shapes[shape_name] = self._parse_shape(shape_name, shape_data)

        return ServiceModel(
            operations=operations,
            shapes=shapes,
            service_name=metadata.get("serviceId", ""),
            api_version=metadata.get("apiVersion", ""),
        )

    def _parse_operation(self, name: str, data: dict) -> OperationInfo:
        """Parsea una operación individual."""
        input_shape = data.get("input", {}).get("shape")
        output_shape = data.get("output", {}).get("shape")
        doc = data.get("documentation")

        return OperationInfo(
            name=name,
            documentation=doc,
            input_shape_name=input_shape,
            output_shape_name=output_shape,
        )

    def _parse_shape(self, name: str, data: dict) -> ShapeInfo:
        """Parsea un shape individual."""
        shape_type = data.get("type", "string")
        doc = data.get("documentation")

        members = None
        required_members = None
        member_shape = None
        key_shape = None
        value_shape = None
        enum_values = None

        if shape_type == "structure":
            raw_members = data.get("members", {})
            members = {}
            for member_name, member_data in raw_members.items():
                members[member_name] = MemberInfo(
                    name=member_name,
                    shape_name=member_data.get("shape", ""),
                    documentation=member_data.get("documentation"),
                )
            required_members = data.get("required", [])

        elif shape_type == "list":
            member_data = data.get("member", {})
            member_shape = member_data.get("shape")

        elif shape_type == "map":
            key_shape = data.get("key", {}).get("shape")
            value_shape = data.get("value", {}).get("shape")

        if shape_type == "string" and "enum" in data:
            enum_values = data["enum"]

        return ShapeInfo(
            name=name,
            shape_type=shape_type,
            documentation=doc,
            members=members,
            required_members=required_members,
            member_shape=member_shape,
            key_shape=key_shape,
            value_shape=value_shape,
            enum_values=enum_values,
        )
