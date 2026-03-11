"""Tests para ServiceModelParser.

Property 1: Round-trip del parseo del Service Model
**Validates: Requirements 1.6**

Property 4: Completitud de extracción de miembros de shapes structure
**Validates: Requirements 1.3**
"""

import json
import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from sagemaker_catalog_mcp_server.parser import (
    ServiceModelParser,
    ServiceModelNotFoundError,
    ServiceModelParseError,
)


# --- Estrategias ---

@st.composite
def random_members(draw):
    """Genera miembros aleatorios para un shape structure."""
    num = draw(st.integers(min_value=0, max_value=5))
    members = {}
    for i in range(num):
        name = f"member{i}"
        members[name] = {"shape": "StringShape", "documentation": f"<p>Doc for {name}</p>"}
    num_required = draw(st.integers(min_value=0, max_value=num))
    required = list(members.keys())[:num_required]
    return members, required


@st.composite
def random_service_model(draw):
    """Genera un service model JSON aleatorio mínimo."""
    num_ops = draw(st.integers(min_value=1, max_value=5))
    operations = {}
    shapes = {"StringShape": {"type": "string"}}

    for i in range(num_ops):
        op_name = f"Operation{i}"
        input_name = f"Op{i}Input"
        output_name = f"Op{i}Output"

        members, required = draw(random_members())

        operations[op_name] = {
            "name": op_name,
            "http": {"method": "GET", "requestUri": f"/op{i}"},
            "input": {"shape": input_name},
            "output": {"shape": output_name},
            "documentation": f"<p>Doc for {op_name}</p>",
        }
        shapes[input_name] = {
            "type": "structure",
            "members": members,
            "required": required,
        }
        shapes[output_name] = {"type": "structure", "members": {}}

    return {
        "version": "2.0",
        "metadata": {
            "apiVersion": "2018-05-10",
            "serviceId": "TestService",
        },
        "operations": operations,
        "shapes": shapes,
    }


# --- Property 1: Round-trip del parseo ---

class TestProperty1RoundTrip:
    """Property 1: Round-trip del parseo del Service Model.
    **Validates: Requirements 1.6**
    """

    @given(raw=random_service_model())
    @settings(max_examples=100)
    def test_round_trip_operations_preserved(self, raw: dict):
        """Parsear y verificar que las operaciones se preservan."""
        parser = ServiceModelParser()
        model = parser.parse_from_dict(raw)

        assert set(model.operations.keys()) == set(raw["operations"].keys())
        for op_name, op in model.operations.items():
            raw_op = raw["operations"][op_name]
            assert op.name == op_name
            assert op.input_shape_name == raw_op.get("input", {}).get("shape")
            assert op.output_shape_name == raw_op.get("output", {}).get("shape")

    @given(raw=random_service_model())
    @settings(max_examples=100)
    def test_round_trip_shapes_preserved(self, raw: dict):
        """Parsear y verificar que los shapes se preservan."""
        parser = ServiceModelParser()
        model = parser.parse_from_dict(raw)

        assert set(model.shapes.keys()) == set(raw["shapes"].keys())


# --- Property 4: Completitud de extracción de miembros ---

class TestProperty4MemberCompleteness:
    """Property 4: Completitud de extracción de miembros de shapes structure.
    **Validates: Requirements 1.3**
    """

    @given(raw=random_service_model())
    @settings(max_examples=100)
    def test_structure_members_complete(self, raw: dict):
        """Para cada structure, todos los miembros se extraen correctamente."""
        parser = ServiceModelParser()
        model = parser.parse_from_dict(raw)

        for shape_name, shape in model.shapes.items():
            if shape.shape_type != "structure":
                continue
            raw_shape = raw["shapes"][shape_name]
            raw_members = raw_shape.get("members", {})
            raw_required = raw_shape.get("required", [])

            parsed_members = shape.members or {}
            assert len(parsed_members) == len(raw_members), (
                f"Shape {shape_name}: expected {len(raw_members)} members, got {len(parsed_members)}"
            )
            assert set(parsed_members.keys()) == set(raw_members.keys())
            assert (shape.required_members or []) == raw_required


# --- Unit tests ---

class TestServiceModelParserUnit:
    """Unit tests para ServiceModelParser.
    _Requirements: 13.1, 13.5_
    """

    def test_parse_minimal_model(self, minimal_service_model):
        parser = ServiceModelParser()
        model = parser.parse_from_dict(minimal_service_model)
        assert len(model.operations) == 2
        assert "ListDomains" in model.operations
        assert "GetDomain" in model.operations
        assert model.service_name == "DataZone"
        assert model.api_version == "2018-05-10"

    def test_parse_operation_details(self, minimal_service_model):
        parser = ServiceModelParser()
        model = parser.parse_from_dict(minimal_service_model)
        op = model.operations["GetDomain"]
        assert op.input_shape_name == "GetDomainInput"
        assert op.output_shape_name == "GetDomainOutput"
        assert op.documentation is not None

    def test_parse_structure_shape(self, minimal_service_model):
        parser = ServiceModelParser()
        model = parser.parse_from_dict(minimal_service_model)
        shape = model.shapes["GetDomainInput"]
        assert shape.shape_type == "structure"
        assert "identifier" in shape.members
        assert shape.required_members == ["identifier"]

    def test_parse_enum_shape(self, minimal_service_model):
        parser = ServiceModelParser()
        model = parser.parse_from_dict(minimal_service_model)
        shape = model.shapes["DomainStatus"]
        assert shape.shape_type == "string"
        assert "AVAILABLE" in shape.enum_values

    def test_parse_list_shape(self, minimal_service_model):
        parser = ServiceModelParser()
        model = parser.parse_from_dict(minimal_service_model)
        shape = model.shapes["DomainSummaries"]
        assert shape.shape_type == "list"
        assert shape.member_shape == "DomainSummary"

    def test_parse_map_shape(self, minimal_service_model):
        parser = ServiceModelParser()
        model = parser.parse_from_dict(minimal_service_model)
        shape = model.shapes["Tags"]
        assert shape.shape_type == "map"
        assert shape.key_shape == "TagKey"
        assert shape.value_shape == "TagValue"

    def test_parse_empty_shapes(self):
        raw = {
            "metadata": {"serviceId": "Test", "apiVersion": "1.0"},
            "operations": {},
            "shapes": {},
        }
        parser = ServiceModelParser()
        model = parser.parse_from_dict(raw)
        assert len(model.operations) == 0
        assert len(model.shapes) == 0

    def test_find_service_model_path(self):
        parser = ServiceModelParser()
        path = parser.find_service_model_path()
        assert Path(path).exists()
        assert "datazone" in path

    def test_parse_real_service_model(self):
        parser = ServiceModelParser()
        model = parser.parse()
        assert len(model.operations) >= 170
        assert len(model.shapes) >= 1000

    def test_file_not_found_error(self):
        parser = ServiceModelParser()
        with pytest.raises(ServiceModelParseError):
            parser.parse("/nonexistent/path/service-2.json")
