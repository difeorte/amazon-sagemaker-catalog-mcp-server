"""Tests para TypeConverter — conversión de tipos botocore a JSON Schema.

Property 7: Conversión de tipos botocore a JSON Schema
**Validates: Requirements 2.5**

Property 5: Resolución recursiva de shapes anidados
**Validates: Requirements 1.4**
"""

import json

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from sagemaker_catalog_mcp_server.models import ShapeInfo
from sagemaker_catalog_mcp_server.utils.type_converter import TypeConverter

# --- Estrategias de generación ---

PRIMITIVE_TYPES = ["string", "integer", "long", "float", "double", "boolean", "timestamp", "blob"]

EXPECTED_JSON_TYPES = {
    "string": "string",
    "integer": "integer",
    "long": "integer",
    "float": "number",
    "double": "number",
    "boolean": "boolean",
    "timestamp": "string",
    "blob": "string",
}

EXPECTED_FORMATS = {
    "timestamp": "date-time",
    "blob": "base64",
}


@st.composite
def primitive_shape_strategy(draw):
    """Genera un ShapeInfo primitivo aleatorio."""
    shape_type = draw(st.sampled_from(PRIMITIVE_TYPES))
    name = draw(st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz", min_size=1, max_size=20))
    enum_values = None
    if shape_type == "string":
        has_enum = draw(st.booleans())
        if has_enum:
            enum_values = draw(st.lists(
                st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ_", min_size=1, max_size=15),
                min_size=1, max_size=5, unique=True,
            ))
    return ShapeInfo(name=name, shape_type=shape_type, enum_values=enum_values)


@st.composite
def list_shape_with_member(draw):
    """Genera un shape list con su member shape."""
    member_type = draw(st.sampled_from(PRIMITIVE_TYPES))
    member_name = "MemberShape"
    list_name = "ListShape"
    member_shape = ShapeInfo(name=member_name, shape_type=member_type)
    list_shape = ShapeInfo(name=list_name, shape_type="list", member_shape=member_name)
    return list_shape, {member_name: member_shape, list_name: list_shape}


@st.composite
def map_shape_with_members(draw):
    """Genera un shape map con key y value shapes."""
    value_type = draw(st.sampled_from(PRIMITIVE_TYPES))
    key_name = "KeyShape"
    value_name = "ValueShape"
    map_name = "MapShape"
    key_shape = ShapeInfo(name=key_name, shape_type="string")
    value_shape = ShapeInfo(name=value_name, shape_type=value_type)
    map_shape = ShapeInfo(name=map_name, shape_type="map", key_shape=key_name, value_shape=value_name)
    return map_shape, {key_name: key_shape, value_name: value_shape, map_name: map_shape}


@st.composite
def nested_shapes_strategy(draw):
    """Genera un grafo de shapes con nesting arbitrario (list/map/structure) que termina en primitivos.

    Produce el nombre del shape raíz y el diccionario completo de shapes.
    El depth varía de 1 a 5 niveles.
    """
    depth = draw(st.integers(min_value=1, max_value=5))
    shapes: dict[str, ShapeInfo] = {}
    counter = 0

    def _name():
        nonlocal counter
        counter += 1
        return f"Shape{counter}"

    # Construir cadena de shapes de abajo hacia arriba
    # Capa más profunda: siempre un primitivo
    leaf_type = draw(st.sampled_from(PRIMITIVE_TYPES))
    leaf_name = _name()
    shapes[leaf_name] = ShapeInfo(name=leaf_name, shape_type=leaf_type)
    child_name = leaf_name

    for _ in range(depth):
        wrapper_kind = draw(st.sampled_from(["list", "map", "structure"]))
        wrapper_name = _name()

        if wrapper_kind == "list":
            shapes[wrapper_name] = ShapeInfo(
                name=wrapper_name, shape_type="list", member_shape=child_name,
            )
        elif wrapper_kind == "map":
            key_name = _name()
            shapes[key_name] = ShapeInfo(name=key_name, shape_type="string")
            shapes[wrapper_name] = ShapeInfo(
                name=wrapper_name, shape_type="map",
                key_shape=key_name, value_shape=child_name,
            )
        else:  # structure
            from sagemaker_catalog_mcp_server.models import MemberInfo
            member_field = "field1"
            shapes[wrapper_name] = ShapeInfo(
                name=wrapper_name, shape_type="structure",
                members={member_field: MemberInfo(name=member_field, shape_name=child_name)},
                required_members=[member_field],
            )
        child_name = wrapper_name

    # Optionally add a cycle (self-referencing shape) to test cycle detection
    add_cycle = draw(st.booleans())
    if add_cycle:
        cycle_a = _name()
        cycle_b = _name()
        shapes[cycle_a] = ShapeInfo(name=cycle_a, shape_type="list", member_shape=cycle_b)
        shapes[cycle_b] = ShapeInfo(name=cycle_b, shape_type="list", member_shape=cycle_a)

    root_name = child_name
    return root_name, shapes


# --- Property 7: Conversión de tipos primitivos ---

class TestProperty7TypeConversion:
    """Property 7: Conversión de tipos botocore a JSON Schema.
    **Validates: Requirements 2.5**
    """

    @given(shape=primitive_shape_strategy())
    @settings(max_examples=100)
    def test_primitive_type_maps_correctly(self, shape: ShapeInfo):
        """Para cualquier tipo primitivo, la conversión produce el tipo JSON Schema correcto."""
        shapes = {shape.name: shape}
        converter = TypeConverter(shapes)
        schema = converter.to_json_schema(shape.name)

        expected_type = EXPECTED_JSON_TYPES[shape.shape_type]
        assert schema["type"] == expected_type, (
            f"{shape.shape_type} debería mapear a {expected_type}, got {schema['type']}"
        )

        if shape.shape_type in EXPECTED_FORMATS:
            assert schema.get("format") == EXPECTED_FORMATS[shape.shape_type]

        if shape.enum_values:
            assert schema["enum"] == shape.enum_values


# --- Property 5: Resolución recursiva ---

class TestProperty5RecursiveResolution:
    """Property 5: Resolución recursiva de shapes anidados.
    **Validates: Requirements 1.4**
    """

    @given(data=list_shape_with_member())
    @settings(max_examples=100)
    def test_list_resolves_to_array(self, data):
        """Para cualquier shape list, la resolución produce un JSON Schema array válido."""
        list_shape, shapes = data
        converter = TypeConverter(shapes)
        schema = converter.to_json_schema(list_shape.name)

        assert schema["type"] == "array"
        assert "items" in schema

    @given(data=map_shape_with_members())
    @settings(max_examples=100)
    def test_map_resolves_to_object(self, data):
        """Para cualquier shape map, la resolución produce un JSON Schema object con additionalProperties."""
        map_shape, shapes = data
        converter = TypeConverter(shapes)
        schema = converter.to_json_schema(map_shape.name)

        assert schema["type"] == "object"
        assert "additionalProperties" in schema

    @given(data=nested_shapes_strategy())
    @settings(max_examples=100)
    def test_nested_shapes_terminate_and_produce_valid_schema(self, data):
        """Para cualquier grafo de shapes anidados (list/map/structure, con posibles ciclos),
        la resolución recursiva debe terminar y producir un JSON Schema serializable
        con la estructura correcta (array para list, object para map/structure).
        """
        root_name, shapes = data
        converter = TypeConverter(shapes)
        schema = converter.to_json_schema(root_name)

        # Must terminate (we got here) and be JSON-serializable
        json.dumps(schema)

        # Root schema type must match the root shape type
        root_shape = shapes[root_name]
        if root_shape.shape_type == "list":
            assert schema["type"] == "array"
            assert "items" in schema
        elif root_shape.shape_type == "map":
            assert schema["type"] == "object"
            assert "additionalProperties" in schema
        elif root_shape.shape_type == "structure":
            assert schema["type"] == "object"
            assert "properties" in schema
        else:
            # primitive at root
            assert "type" in schema

    def test_cyclic_shapes_terminate(self):
        """Shapes con ciclos deben terminar sin loop infinito."""
        shapes = {
            "A": ShapeInfo(name="A", shape_type="list", member_shape="B"),
            "B": ShapeInfo(name="B", shape_type="list", member_shape="A"),
        }
        converter = TypeConverter(shapes)
        schema = converter.to_json_schema("A")
        # Debe terminar y producir un schema válido
        assert schema["type"] == "array"
        json.dumps(schema)  # Debe ser serializable

    def test_cycle_returns_object_type(self):
        """Cuando se detecta un ciclo directo, retorna {"type": "object"}."""
        shapes = {
            "Self": ShapeInfo(name="Self", shape_type="list", member_shape="Self"),
        }
        converter = TypeConverter(shapes)
        schema = converter.to_json_schema("Self")
        assert schema["type"] == "array"
        # El items debe ser object (ciclo detectado)
        assert schema["items"]["type"] == "object"


# --- Unit tests ---

class TestTypeConverterUnit:
    """Unit tests para TypeConverter.
    _Requirements: 13.3_
    """

    def test_string_type(self):
        shapes = {"S": ShapeInfo(name="S", shape_type="string")}
        assert TypeConverter(shapes).to_json_schema("S")["type"] == "string"

    def test_integer_type(self):
        shapes = {"I": ShapeInfo(name="I", shape_type="integer")}
        assert TypeConverter(shapes).to_json_schema("I")["type"] == "integer"

    def test_long_type(self):
        shapes = {"L": ShapeInfo(name="L", shape_type="long")}
        assert TypeConverter(shapes).to_json_schema("L")["type"] == "integer"

    def test_float_type(self):
        shapes = {"F": ShapeInfo(name="F", shape_type="float")}
        assert TypeConverter(shapes).to_json_schema("F")["type"] == "number"

    def test_double_type(self):
        shapes = {"D": ShapeInfo(name="D", shape_type="double")}
        assert TypeConverter(shapes).to_json_schema("D")["type"] == "number"

    def test_boolean_type(self):
        shapes = {"B": ShapeInfo(name="B", shape_type="boolean")}
        assert TypeConverter(shapes).to_json_schema("B")["type"] == "boolean"

    def test_timestamp_type(self):
        shapes = {"T": ShapeInfo(name="T", shape_type="timestamp")}
        schema = TypeConverter(shapes).to_json_schema("T")
        assert schema["type"] == "string"
        assert schema["format"] == "date-time"

    def test_blob_type(self):
        shapes = {"B": ShapeInfo(name="B", shape_type="blob")}
        schema = TypeConverter(shapes).to_json_schema("B")
        assert schema["type"] == "string"
        assert schema["format"] == "base64"

    def test_string_with_enum(self):
        shapes = {"E": ShapeInfo(name="E", shape_type="string", enum_values=["A", "B", "C"])}
        schema = TypeConverter(shapes).to_json_schema("E")
        assert schema["type"] == "string"
        assert schema["enum"] == ["A", "B", "C"]

    def test_structure_with_required(self):
        from sagemaker_catalog_mcp_server.models import MemberInfo
        shapes = {
            "S": ShapeInfo(
                name="S", shape_type="structure",
                members={"id": MemberInfo(name="id", shape_name="Str"), "name": MemberInfo(name="name", shape_name="Str")},
                required_members=["id"],
            ),
            "Str": ShapeInfo(name="Str", shape_type="string"),
        }
        schema = TypeConverter(shapes).to_json_schema("S")
        assert schema["type"] == "object"
        assert "id" in schema["properties"]
        assert "name" in schema["properties"]
        assert schema["required"] == ["id"]

    def test_nested_list_of_list(self):
        shapes = {
            "Outer": ShapeInfo(name="Outer", shape_type="list", member_shape="Inner"),
            "Inner": ShapeInfo(name="Inner", shape_type="list", member_shape="Str"),
            "Str": ShapeInfo(name="Str", shape_type="string"),
        }
        schema = TypeConverter(shapes).to_json_schema("Outer")
        assert schema["type"] == "array"
        assert schema["items"]["type"] == "array"
        assert schema["items"]["items"]["type"] == "string"

    def test_map_type(self):
        shapes = {
            "M": ShapeInfo(name="M", shape_type="map", key_shape="K", value_shape="V"),
            "K": ShapeInfo(name="K", shape_type="string"),
            "V": ShapeInfo(name="V", shape_type="integer"),
        }
        schema = TypeConverter(shapes).to_json_schema("M")
        assert schema["type"] == "object"
        assert schema["additionalProperties"]["type"] == "integer"

    def test_nested_structure(self):
        from sagemaker_catalog_mcp_server.models import MemberInfo
        shapes = {
            "Outer": ShapeInfo(
                name="Outer", shape_type="structure",
                members={"inner": MemberInfo(name="inner", shape_name="Inner")},
            ),
            "Inner": ShapeInfo(
                name="Inner", shape_type="structure",
                members={"value": MemberInfo(name="value", shape_name="Str")},
                required_members=["value"],
            ),
            "Str": ShapeInfo(name="Str", shape_type="string"),
        }
        schema = TypeConverter(shapes).to_json_schema("Outer")
        assert schema["type"] == "object"
        inner = schema["properties"]["inner"]
        assert inner["type"] == "object"
        assert inner["properties"]["value"]["type"] == "string"
        assert inner["required"] == ["value"]

    def test_cyclic_shape_terminates(self):
        shapes = {
            "A": ShapeInfo(name="A", shape_type="list", member_shape="B"),
            "B": ShapeInfo(name="B", shape_type="list", member_shape="A"),
        }
        schema = TypeConverter(shapes).to_json_schema("A")
        assert schema["type"] == "array"
        # B resolves to array, but its items (A) hits cycle → object
        assert schema["items"]["type"] == "array"
        assert schema["items"]["items"]["type"] == "object"

    def test_unknown_shape_returns_object(self):
        converter = TypeConverter({})
        schema = converter.to_json_schema("NonExistent")
        assert schema["type"] == "object"
