"""Tests para ToolGenerator.

Property 3: Conteo y unicidad de tools generadas
**Validates: Requirements 2.1, 2.6, 10.2, 12.1**

Property 6: Fidelidad de tool definitions respecto al Service Model
**Validates: Requirements 2.3, 2.4**
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from sagemaker_catalog_mcp_server.models import (
    MemberInfo,
    OperationInfo,
    ServiceModel,
    ShapeInfo,
)
from sagemaker_catalog_mcp_server.generator import ToolGenerator


# --- Estrategias ---

@st.composite
def random_service_model_for_gen(draw):
    """Genera un ServiceModel aleatorio para testing del generador."""
    num_ops = draw(st.integers(min_value=1, max_value=10))
    operations = {}
    shapes = {}

    for i in range(num_ops):
        op_name = f"Operation{i:03d}"
        input_name = f"Op{i}Input"

        num_members = draw(st.integers(min_value=0, max_value=4))
        members = {}
        for j in range(num_members):
            m_name = f"field{j}"
            shape_name = f"Field{j}Shape"
            members[m_name] = MemberInfo(name=m_name, shape_name=shape_name, documentation=f"<p>Field {j}</p>")
            shapes[shape_name] = ShapeInfo(name=shape_name, shape_type="string")

        num_required = draw(st.integers(min_value=0, max_value=num_members))
        required = list(members.keys())[:num_required]

        operations[op_name] = OperationInfo(
            name=op_name,
            documentation=f"<p>Documentation for {op_name}</p>",
            input_shape_name=input_name,
            output_shape_name=None,
        )
        shapes[input_name] = ShapeInfo(
            name=input_name,
            shape_type="structure",
            members=members,
            required_members=required,
        )

    return ServiceModel(operations=operations, shapes=shapes, service_name="Test", api_version="1.0")


# --- Property 3: Conteo y unicidad ---

class TestProperty3CountAndUniqueness:
    """Property 3: Conteo y unicidad de tools generadas.
    **Validates: Requirements 2.1, 2.6, 10.2, 12.1**
    """

    @given(model=random_service_model_for_gen())
    @settings(max_examples=100)
    def test_tool_count_matches_operations(self, model: ServiceModel):
        """El generador produce exactamente N tools para N operaciones."""
        gen = ToolGenerator(model)
        tools = gen.generate_all()
        assert len(tools) == len(model.operations)

    @given(model=random_service_model_for_gen())
    @settings(max_examples=100)
    def test_tool_names_unique(self, model: ServiceModel):
        """Todos los nombres de tools son únicos."""
        gen = ToolGenerator(model)
        tools = gen.generate_all()
        names = [t.tool_name for t in tools]
        assert len(names) == len(set(names))


# --- Property 6: Fidelidad ---

class TestProperty6Fidelity:
    """Property 6: Fidelidad de tool definitions respecto al Service Model.
    **Validates: Requirements 2.3, 2.4**
    """

    @given(model=random_service_model_for_gen())
    @settings(max_examples=100)
    def test_description_derived_from_documentation(self, model: ServiceModel):
        """La descripción de cada tool se deriva de la documentación de la operación."""
        gen = ToolGenerator(model)
        tools = gen.generate_all()
        for tool in tools:
            op = model.operations[tool.operation_name]
            if op.documentation:
                # La descripción debe contener algo del texto original (sin HTML)
                assert len(tool.description) > 0
                assert "<p>" not in tool.description  # HTML limpiado

    @given(model=random_service_model_for_gen())
    @settings(max_examples=100)
    def test_required_params_match_input_shape(self, model: ServiceModel):
        """Los required_params coinciden con los required del input shape."""
        gen = ToolGenerator(model)
        tools = gen.generate_all()
        for tool in tools:
            op = model.operations[tool.operation_name]
            if op.input_shape_name and op.input_shape_name in model.shapes:
                shape = model.shapes[op.input_shape_name]
                expected_required = shape.required_members or []
                assert tool.required_params == expected_required


# --- Unit tests ---

class TestToolGeneratorUnit:
    """Unit tests para ToolGenerator.
    _Requirements: 13.1, 13.4_
    """

    def test_generate_with_real_service_model(self):
        from sagemaker_catalog_mcp_server.parser import ServiceModelParser
        parser = ServiceModelParser()
        model = parser.parse()
        gen = ToolGenerator(model)
        tools = gen.generate_all()
        assert len(tools) == len(model.operations)
        names = [t.tool_name for t in tools]
        assert len(names) == len(set(names))

    def test_operation_without_input_shape(self):
        model = ServiceModel(
            operations={"NoInput": OperationInfo(name="NoInput", documentation="<p>Test</p>")},
            shapes={},
            service_name="Test",
            api_version="1.0",
        )
        gen = ToolGenerator(model)
        tools = gen.generate_all()
        assert len(tools) == 1
        assert tools[0].tool_name == "no_input"
        assert tools[0].input_schema == {"type": "object", "properties": {}}

    def test_operation_with_complex_shape(self):
        model = ServiceModel(
            operations={
                "CreateThing": OperationInfo(
                    name="CreateThing",
                    documentation="<p>Creates a thing.</p>",
                    input_shape_name="CreateThingInput",
                ),
            },
            shapes={
                "CreateThingInput": ShapeInfo(
                    name="CreateThingInput",
                    shape_type="structure",
                    members={
                        "name": MemberInfo(name="name", shape_name="NameStr"),
                        "tags": MemberInfo(name="tags", shape_name="TagMap"),
                    },
                    required_members=["name"],
                ),
                "NameStr": ShapeInfo(name="NameStr", shape_type="string"),
                "TagMap": ShapeInfo(name="TagMap", shape_type="map", key_shape="TagKey", value_shape="TagVal"),
                "TagKey": ShapeInfo(name="TagKey", shape_type="string"),
                "TagVal": ShapeInfo(name="TagVal", shape_type="string"),
            },
            service_name="Test",
            api_version="1.0",
        )
        gen = ToolGenerator(model)
        tools = gen.generate_all()
        assert len(tools) == 1
        tool = tools[0]
        assert tool.tool_name == "create_thing"
        assert tool.required_params == ["name"]
        assert "name" in tool.input_schema["properties"]
        assert "tags" in tool.input_schema["properties"]
