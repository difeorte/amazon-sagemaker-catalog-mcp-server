"""Tests para NameConverter — conversión PascalCase ↔ snake_case.

Property 2: Round-trip de conversión de nombres PascalCase ↔ snake_case
**Validates: Requirements 10.3, 10.1, 2.2**
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from sagemaker_catalog_mcp_server.utils.name_converter import NameConverter


# Estrategia: generar nombres PascalCase válidos (palabras capitalizadas concatenadas)
@st.composite
def pascal_case_names(draw):
    """Genera nombres PascalCase como los de la API de DataZone."""
    num_words = draw(st.integers(min_value=1, max_value=5))
    words = []
    for _ in range(num_words):
        word = draw(st.text(
            alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz"),
            min_size=2, max_size=10,
        ))
        words.append(word.capitalize())
    return "".join(words)


class TestProperty2RoundTrip:
    """Property 2: Round-trip de conversión de nombres PascalCase ↔ snake_case.
    **Validates: Requirements 10.3, 10.1, 2.2**
    """

    @given(name=pascal_case_names())
    @settings(max_examples=100)
    def test_round_trip_pascal_to_snake_to_pascal(self, name: str):
        """Para cualquier nombre PascalCase, to_snake_case → to_pascal_case produce el original."""
        snake = NameConverter.to_snake_case(name)
        back = NameConverter.to_pascal_case(snake)
        assert back == name, f"{name} → {snake} → {back}"

    @given(name=pascal_case_names())
    @settings(max_examples=100)
    def test_snake_case_is_lowercase_with_underscores(self, name: str):
        """El resultado de to_snake_case solo contiene minúsculas y underscores."""
        snake = NameConverter.to_snake_case(name)
        assert snake == snake.lower()
        assert all(c.isalpha() or c == "_" for c in snake)


class TestNameConverterUnit:
    """Unit tests para NameConverter.
    _Requirements: 13.2_
    """

    def test_list_domains(self):
        assert NameConverter.to_snake_case("ListDomains") == "list_domains"
        assert NameConverter.to_pascal_case("list_domains") == "ListDomains"

    def test_create_asset_type(self):
        assert NameConverter.to_snake_case("CreateAssetType") == "create_asset_type"
        assert NameConverter.to_pascal_case("create_asset_type") == "CreateAssetType"

    def test_single_word(self):
        assert NameConverter.to_snake_case("Search") == "search"
        assert NameConverter.to_pascal_case("search") == "Search"

    def test_accept_predictions(self):
        assert NameConverter.to_snake_case("AcceptPredictions") == "accept_predictions"

    def test_get_domain(self):
        assert NameConverter.to_snake_case("GetDomain") == "get_domain"

    def test_cancel_metadata_generation_run(self):
        assert NameConverter.to_snake_case("CancelMetadataGenerationRun") == "cancel_metadata_generation_run"

    def test_all_real_datazone_operations_round_trip(self):
        """Verifica round-trip con las operaciones reales de DataZone."""
        from sagemaker_catalog_mcp_server.parser import ServiceModelParser
        parser = ServiceModelParser()
        model = parser.parse()
        for op_name in model.operations:
            snake = NameConverter.to_snake_case(op_name)
            back = NameConverter.to_pascal_case(snake)
            assert back == op_name, f"{op_name} → {snake} → {back}"
