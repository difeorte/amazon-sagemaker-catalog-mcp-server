"""Tests de integración para el servidor MCP.
_Requirements: 3.1, 3.2, 11.1_
"""

from unittest.mock import patch

from sagemaker_catalog_mcp_server.server import SageMakerCatalogMCPServer


class TestServerInitialization:
    """Tests de inicialización del servidor."""

    def test_initialize_registers_all_tools(self):
        """El servidor registra una tool por cada operación del service model."""
        with patch("sagemaker_catalog_mcp_server.executor.boto3"):
            server = SageMakerCatalogMCPServer()
            server.initialize()

            assert len(server.tools) >= 170

            # Verificar que los nombres son snake_case
            for tool_name in server.tools:
                assert tool_name == tool_name.lower()

    def test_tool_names_include_known_operations(self):
        """Las tools incluyen operaciones conocidas del server existente."""
        with patch("sagemaker_catalog_mcp_server.executor.boto3"):
            server = SageMakerCatalogMCPServer()
            server.initialize()

            expected_tools = [
                "list_domains", "get_domain", "create_project",
                "list_projects", "search", "search_listings",
                "create_glossary", "create_glossary_term",
            ]
            for name in expected_tools:
                assert name in server.tools, f"Missing expected tool: {name}"

    def test_tool_definitions_have_descriptions(self):
        """Todas las tools tienen descripción no vacía."""
        with patch("sagemaker_catalog_mcp_server.executor.boto3"):
            server = SageMakerCatalogMCPServer()
            server.initialize()

            for tool_name, (mcp_tool, tool_def) in server.tools.items():
                assert mcp_tool.description, f"Tool {tool_name} has no description"
                assert len(mcp_tool.description) > 5

    def test_tool_definitions_have_input_schemas(self):
        """Todas las tools tienen input schema con type object."""
        with patch("sagemaker_catalog_mcp_server.executor.boto3"):
            server = SageMakerCatalogMCPServer()
            server.initialize()

            for tool_name, (mcp_tool, tool_def) in server.tools.items():
                assert mcp_tool.inputSchema.get("type") == "object", (
                    f"Tool {tool_name} schema type is not 'object'"
                )

    def test_includes_all_49_existing_server_tools(self):
        """Verifica que las 49 tools del server existente awslabs/amazon-datazone-mcp-server están incluidas.
        _Requirements: 11.1_
        """
        with patch("sagemaker_catalog_mcp_server.executor.boto3"):
            server = SageMakerCatalogMCPServer()
            server.initialize()

            # Las 49 operaciones cubiertas por awslabs/amazon-datazone-mcp-server v0.1.1
            existing_server_tools = [
                "list_domains", "get_domain", "create_domain", "delete_domain",
                "create_project", "delete_project", "get_project", "list_projects",
                "create_project_membership", "delete_project_membership", "list_project_memberships",
                "create_asset", "delete_asset", "get_asset",
                "create_asset_filter",
                "create_data_source", "delete_data_source", "get_data_source", "list_data_sources",
                "start_data_source_run", "get_data_source_run", "list_data_source_runs",
                "list_data_source_run_activities",
                "create_connection", "delete_connection", "get_connection", "list_connections",
                "search", "search_listings", "search_types", "search_user_profiles",
                "create_glossary", "delete_glossary", "get_glossary", "update_glossary",
                "create_glossary_term", "delete_glossary_term", "get_glossary_term", "update_glossary_term",
                "create_environment", "delete_environment", "get_environment", "list_environments",
                "create_environment_profile", "delete_environment_profile",
                "get_environment_profile", "list_environment_profiles",
                "create_subscription_request", "accept_subscription_request",
            ]

            assert len(existing_server_tools) == 49
            missing = [t for t in existing_server_tools if t not in server.tools]
            assert not missing, f"Missing tools from existing server: {missing}"
