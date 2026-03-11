"""Tests para ToolExecutor.

Property 8: Serialización de respuestas boto3 a JSON
**Validates: Requirements 4.2**

Property 10: Errores de AWS se estructuran correctamente
**Validates: Requirements 4.4**

Property 9: Validación rechaza entradas inválidas
**Validates: Requirements 4.3**
"""

import json
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from sagemaker_catalog_mcp_server.executor import ToolExecutor, ToolExecutionError


# --- Helpers ---

def make_executor_with_mock():
    """Crea un ToolExecutor con cliente boto3 mockeado."""
    with patch("sagemaker_catalog_mcp_server.executor.boto3") as mock_boto3:
        mock_client = MagicMock()
        mock_boto3.Session.return_value.client.return_value = mock_client
        executor = ToolExecutor()
        return executor, mock_client


# --- Property 8: Serialización ---

class TestProperty8Serialization:
    """Property 8: Serialización de respuestas boto3 a JSON.
    **Validates: Requirements 4.2**
    """

    @given(
        dt=st.datetimes(
            min_value=datetime(2000, 1, 1),
            max_value=datetime(2030, 12, 31),
        ),
    )
    @settings(max_examples=100)
    def test_datetime_serializes_to_valid_json(self, dt):
        """Cualquier datetime se serializa a JSON válido."""
        executor, mock_client = make_executor_with_mock()
        mock_client.list_domains.return_value = {
            "ResponseMetadata": {},
            "createdAt": dt,
        }
        result = executor.execute("ListDomains", {})
        json_str = json.dumps(result)
        parsed = json.loads(json_str)
        assert isinstance(parsed["createdAt"], str)

    @given(data=st.binary(min_size=0, max_size=100))
    @settings(max_examples=100)
    def test_bytes_serializes_to_valid_json(self, data):
        """Cualquier bytes se serializa a JSON válido."""
        executor, mock_client = make_executor_with_mock()
        mock_client.list_domains.return_value = {
            "ResponseMetadata": {},
            "binaryData": data,
        }
        result = executor.execute("ListDomains", {})
        json_str = json.dumps(result)
        parsed = json.loads(json_str)
        assert isinstance(parsed["binaryData"], str)

    @given(
        d=st.decimals(
            min_value=-1e10, max_value=1e10,
            allow_nan=False, allow_infinity=False,
        ),
    )
    @settings(max_examples=100)
    def test_decimal_serializes_to_valid_json(self, d):
        """Cualquier Decimal se serializa a JSON válido."""
        executor, mock_client = make_executor_with_mock()
        mock_client.list_domains.return_value = {
            "ResponseMetadata": {},
            "count": d,
        }
        result = executor.execute("ListDomains", {})
        json_str = json.dumps(result)
        parsed = json.loads(json_str)
        assert isinstance(parsed["count"], (int, float))

    @given(
        dt=st.datetimes(min_value=datetime(2000, 1, 1), max_value=datetime(2030, 12, 31)),
        raw_bytes=st.binary(min_size=0, max_size=50),
        dec_val=st.decimals(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
        extra_str=st.text(min_size=0, max_size=30),
        nested_dt=st.datetimes(min_value=datetime(2000, 1, 1), max_value=datetime(2030, 12, 31)),
    )
    @settings(max_examples=100)
    def test_mixed_response_serializes_to_valid_json(self, dt, raw_bytes, dec_val, extra_str, nested_dt):
        """Respuestas con mezcla de datetime, bytes, Decimal y tipos anidados se serializan a JSON válido."""
        executor, mock_client = make_executor_with_mock()
        mock_client.list_domains.return_value = {
            "ResponseMetadata": {"RequestId": "abc"},
            "createdAt": dt,
            "binaryPayload": raw_bytes,
            "count": dec_val,
            "name": extra_str,
            "items": [
                {"updatedAt": nested_dt, "data": raw_bytes, "score": Decimal("1.5")},
            ],
            "metadata": {"ts": dt, "raw": raw_bytes},
        }
        result = executor.execute("ListDomains", {})
        # Must produce valid JSON
        json_str = json.dumps(result)
        parsed = json.loads(json_str)
        # ResponseMetadata stripped
        assert "ResponseMetadata" not in parsed
        # All non-JSON-native types converted
        assert isinstance(parsed["createdAt"], str)
        assert isinstance(parsed["binaryPayload"], str)
        assert isinstance(parsed["count"], (int, float))
        assert isinstance(parsed["items"][0]["updatedAt"], str)
        assert isinstance(parsed["items"][0]["data"], str)
        assert isinstance(parsed["items"][0]["score"], (int, float))
        assert isinstance(parsed["metadata"]["ts"], str)
        assert isinstance(parsed["metadata"]["raw"], str)


# --- Property 10: Errores estructurados ---

class TestProperty10ErrorStructure:
    """Property 10: Errores de AWS se estructuran correctamente.
    **Validates: Requirements 4.4**
    """

    @given(
        error_code=st.text(
            alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
            min_size=3, max_size=30,
        ),
        error_message=st.text(min_size=1, max_size=100),
    )
    @settings(max_examples=100)
    def test_client_error_contains_code_message_operation(self, error_code, error_message):
        """Para cualquier ClientError con código y mensaje arbitrarios, el error
        resultante debe contener el código, el mensaje, y el nombre de la operación."""
        from botocore.exceptions import ClientError

        executor, mock_client = make_executor_with_mock()
        mock_client.list_domains.side_effect = ClientError(
            {"Error": {"Code": error_code, "Message": error_message}},
            "ListDomains",
        )

        with pytest.raises(ToolExecutionError) as exc_info:
            executor.execute("ListDomains", {})

        err = exc_info.value
        assert err.error_code == error_code
        assert error_message in err.message
        assert err.operation == "ListDomains"

    @given(
        error_code=st.sampled_from([
            "AccessDeniedException", "ResourceNotFoundException",
            "ThrottlingException", "ValidationException",
            "ConflictException", "ServiceQuotaExceededException",
            "InternalServerException",
        ]),
        error_message=st.text(min_size=1, max_size=200),
        operation_name=st.sampled_from([
            "ListDomains", "GetDomain", "CreateProject",
            "DeleteAsset", "UpdateGlossaryTerm", "SearchListings",
        ]),
    )
    @settings(max_examples=100)
    def test_error_structure_across_operations(self, error_code, error_message, operation_name):
        """Para cualquier combinación de código de error AWS, mensaje, y operación,
        el ToolExecutionError resultante preserva los tres campos."""
        from botocore.exceptions import ClientError

        executor, mock_client = make_executor_with_mock()
        # Dynamically set the side_effect on the correct boto3 method
        boto3_method = operation_name[0].lower() + operation_name[1:]
        import re
        boto3_method = re.sub(
            r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "_", operation_name
        ).lower()
        getattr(mock_client, boto3_method).side_effect = ClientError(
            {"Error": {"Code": error_code, "Message": error_message}},
            operation_name,
        )

        with pytest.raises(ToolExecutionError) as exc_info:
            executor.execute(operation_name, {})

        err = exc_info.value
        assert err.error_code == error_code, f"Expected error_code={error_code}, got {err.error_code}"
        assert error_message in err.message, f"Expected message to contain '{error_message}'"
        assert err.operation == operation_name, f"Expected operation={operation_name}, got {err.operation}"


# --- Property 9: Validación rechaza entradas inválidas ---
# Nota: La validación de parámetros la hace boto3 internamente.
# Verificamos que los errores de boto3 se propagan correctamente.

class TestProperty9Validation:
    """Property 9: Validación rechaza entradas inválidas.
    **Validates: Requirements 4.3**

    Para cualquier Tool con campos requeridos en su esquema, invocarla con un
    diccionario de parámetros que omite al menos un campo requerido debe resultar
    en un error de validación (no en una llamada exitosa a la API de AWS).
    """

    @given(
        required_fields=st.lists(
            st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=2, max_size=15),
            min_size=1,
            max_size=5,
            unique=True,
        ),
        operation_name=st.sampled_from([
            "GetDomain", "ListDomains", "CreateProject", "DeleteDomain",
            "GetEnvironment", "CreateAssetType", "ListProjects",
        ]),
    )
    @settings(max_examples=100)
    def test_missing_required_param_raises_error(self, required_fields, operation_name):
        """For any operation with required params, omitting them raises ToolExecutionError,
        never a successful AWS response."""
        from botocore.exceptions import ParamValidationError

        executor, mock_client = make_executor_with_mock()

        # boto3 raises ParamValidationError when required params are missing
        method_mock = MagicMock()
        method_mock.side_effect = ParamValidationError(
            report=f"Missing required parameter(s): {', '.join(required_fields)}"
        )
        # Dynamically set the mock method for the operation
        import re
        method_name = re.sub(
            r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "_", operation_name
        ).lower()
        setattr(mock_client, method_name, method_mock)

        with pytest.raises(ToolExecutionError) as exc_info:
            executor.execute(operation_name, {})

        # The error must contain the operation name
        assert exc_info.value.operation == operation_name
        # The mock method was called (validation happens inside boto3)
        method_mock.assert_called_once_with()

    @given(
        required_fields=st.lists(
            st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=2, max_size=15),
            min_size=2,
            max_size=5,
            unique=True,
        ),
    )
    @settings(max_examples=100)
    def test_partial_required_params_raises_error(self, required_fields):
        """Providing only some required params still raises an error for the missing ones."""
        from botocore.exceptions import ParamValidationError

        executor, mock_client = make_executor_with_mock()

        # Provide only the first field, omit the rest
        provided = {required_fields[0]: "some_value"}
        missing = required_fields[1:]

        mock_client.get_domain.side_effect = ParamValidationError(
            report=f"Missing required parameter(s): {', '.join(missing)}"
        )

        with pytest.raises(ToolExecutionError) as exc_info:
            executor.execute("GetDomain", provided)

        assert exc_info.value.operation == "GetDomain"
        mock_client.get_domain.assert_called_once_with(**provided)


# --- Unit tests ---

class TestToolExecutorUnit:
    """Unit tests para ToolExecutor.
    _Requirements: 13.5_
    """

    def test_successful_execution(self):
        executor, mock_client = make_executor_with_mock()
        mock_client.list_domains.return_value = {
            "ResponseMetadata": {"RequestId": "abc"},
            "items": [{"id": "d-123", "name": "test"}],
        }
        result = executor.execute("ListDomains", {})
        assert "items" in result
        assert "ResponseMetadata" not in result

    def test_datetime_serialization(self):
        executor, mock_client = make_executor_with_mock()
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        mock_client.get_domain.return_value = {
            "ResponseMetadata": {},
            "createdAt": dt,
        }
        result = executor.execute("GetDomain", {"identifier": "d-123"})
        assert result["createdAt"] == "2024-01-15T10:30:00+00:00"

    def test_bytes_serialization(self):
        executor, mock_client = make_executor_with_mock()
        mock_client.get_domain.return_value = {
            "ResponseMetadata": {},
            "data": b"hello",
        }
        result = executor.execute("GetDomain", {"identifier": "d-123"})
        assert result["data"] == "aGVsbG8="  # base64 of "hello"

    def test_decimal_serialization(self):
        executor, mock_client = make_executor_with_mock()
        mock_client.get_domain.return_value = {
            "ResponseMetadata": {},
            "count": Decimal("42"),
            "ratio": Decimal("3.14"),
        }
        result = executor.execute("GetDomain", {"identifier": "d-123"})
        assert result["count"] == 42
        assert result["ratio"] == 3.14

    def test_client_error_handling(self):
        from botocore.exceptions import ClientError

        executor, mock_client = make_executor_with_mock()
        mock_client.list_domains.side_effect = ClientError(
            {"Error": {"Code": "AccessDeniedException", "Message": "Access denied"}},
            "ListDomains",
        )
        with pytest.raises(ToolExecutionError) as exc_info:
            executor.execute("ListDomains", {})
        assert exc_info.value.error_code == "AccessDeniedException"
        assert exc_info.value.operation == "ListDomains"

    def test_credentials_error_handling(self):
        from botocore.exceptions import NoCredentialsError

        executor, mock_client = make_executor_with_mock()
        mock_client.list_domains.side_effect = NoCredentialsError()
        with pytest.raises(ToolExecutionError) as exc_info:
            executor.execute("ListDomains", {})
        assert exc_info.value.error_code == "CredentialsError"

    def test_connection_error_handling(self):
        from botocore.exceptions import EndpointConnectionError

        executor, mock_client = make_executor_with_mock()
        mock_client.list_domains.side_effect = EndpointConnectionError(endpoint_url="https://datazone.us-east-1.amazonaws.com")
        with pytest.raises(ToolExecutionError) as exc_info:
            executor.execute("ListDomains", {})
        assert exc_info.value.error_code == "ConnectionError"

    def test_unsupported_operation(self):
        """Operación que no existe en boto3 produce error."""
        with patch("sagemaker_catalog_mcp_server.executor.boto3") as mock_boto3:
            # Use a real boto3 client as spec so only real methods exist
            import boto3 as real_boto3
            real_client = real_boto3.client("datazone", region_name="us-east-1")
            mock_client = MagicMock(spec=real_client)
            mock_boto3.Session.return_value.client.return_value = mock_client
            executor = ToolExecutor()

            with pytest.raises(ToolExecutionError) as exc_info:
                executor.execute("CompletelyFakeOperation", {})
            assert exc_info.value.error_code == "UnsupportedOperation"

    def test_nested_response_serialization(self):
        executor, mock_client = make_executor_with_mock()
        mock_client.list_domains.return_value = {
            "ResponseMetadata": {},
            "items": [
                {
                    "id": "d-1",
                    "createdAt": datetime(2024, 1, 1, tzinfo=timezone.utc),
                    "tags": {"key": "value"},
                },
            ],
        }
        result = executor.execute("ListDomains", {})
        assert result["items"][0]["createdAt"] == "2024-01-01T00:00:00+00:00"
        assert result["items"][0]["tags"]["key"] == "value"


    def test_snake_case_operation_name_converted(self):
        """Si operation_name viene en snake_case, se convierte a PascalCase antes de llamar a boto3."""
        executor, mock_client = make_executor_with_mock()
        mock_client.list_domains.return_value = {
            "ResponseMetadata": {},
            "items": [],
        }
        result = executor.execute("list_domains", {})
        assert "items" in result
        mock_client.list_domains.assert_called_once_with()
