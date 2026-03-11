"""MCP Server principal para SageMaker Catalog."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Any

from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from sagemaker_catalog_mcp_server.executor import ToolExecutor, ToolExecutionError
from sagemaker_catalog_mcp_server.generator import ToolGenerator
from sagemaker_catalog_mcp_server.models import ToolDefinition
from sagemaker_catalog_mcp_server.parser import (
    ServiceModelParser,
    ServiceModelNotFoundError,
    ServiceModelParseError,
)

logger = logging.getLogger(__name__)


class SageMakerCatalogMCPServer:
    """Servidor MCP que auto-genera tools desde el service model de botocore."""

    def __init__(
        self,
        region: str | None = None,
        profile: str | None = None,
    ):
        self.region = region
        self.profile = profile
        self.server = Server("sagemaker-catalog-mcp-server")
        self.executor: ToolExecutor | None = None
        self.tools: dict[str, tuple[Tool, ToolDefinition]] = {}

    def initialize(self) -> None:
        """Parsea service model, genera tools, y las registra."""
        # 1. Parsear service model
        parser = ServiceModelParser()
        service_model = parser.parse()
        logger.info(
            "Service model parseado: %d operaciones, %d shapes",
            len(service_model.operations),
            len(service_model.shapes),
        )

        # 2. Generar tool definitions
        generator = ToolGenerator(service_model)
        tool_definitions = generator.generate_all()
        logger.info("Generadas %d tool definitions", len(tool_definitions))

        # 3. Crear executor
        self.executor = ToolExecutor(region=self.region, profile=self.profile)

        # 4. Registrar tools con schema correcto
        for tool_def in tool_definitions:
            mcp_tool = Tool(
                name=tool_def.tool_name,
                description=tool_def.description,
                inputSchema=tool_def.input_schema,
            )
            self.tools[tool_def.tool_name] = (mcp_tool, tool_def)

        logger.info("Registradas %d tools", len(self.tools))

        # 5. Registrar handlers
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Registra los handlers de list_tools y call_tool."""

        @self.server.list_tools()
        async def handle_list_tools() -> list[Tool]:
            return [tool for tool, _ in self.tools.values()]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict[str, Any] | None) -> list[TextContent]:
            if name not in self.tools:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": True, "message": f"Tool no encontrada: {name}"})
                )]

            _, tool_def = self.tools[name]
            params = arguments or {}

            try:
                result = self.executor.execute(tool_def.operation_name, params)
                return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]
            except ToolExecutionError as e:
                error_response = {
                    "error": True,
                    "errorCode": e.error_code,
                    "message": e.message,
                    "operation": e.operation,
                }
                return [TextContent(type="text", text=json.dumps(error_response, indent=2, ensure_ascii=False))]

    async def run_stdio(self) -> None:
        """Inicia el servidor con transporte stdio."""
        logger.info("Iniciando servidor con transporte: stdio")
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )


def main() -> None:
    """Entry point del servidor MCP."""
    import asyncio

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )

    parser = argparse.ArgumentParser(description="SageMaker Catalog MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default=os.environ.get("MCP_TRANSPORT", "stdio"),
        help="Transporte MCP (default: stdio)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("MCP_PORT", "8000")),
        help="Puerto para transporte HTTP (default: 8000)",
    )
    parser.add_argument(
        "--region",
        default=os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION")),
        help="Región AWS",
    )
    parser.add_argument(
        "--profile",
        default=os.environ.get("AWS_PROFILE"),
        help="Perfil AWS",
    )
    args = parser.parse_args()

    try:
        server = SageMakerCatalogMCPServer(
            region=args.region,
            profile=args.profile,
        )
        server.initialize()
        asyncio.run(server.run_stdio())
    except (ServiceModelNotFoundError, ServiceModelParseError) as e:
        logger.error("Error de inicialización: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.error("Error inesperado: %s", e)
        sys.exit(1)
