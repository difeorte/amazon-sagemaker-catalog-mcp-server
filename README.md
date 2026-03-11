# Amazon SageMaker Catalog MCP Server

MCP server for Amazon SageMaker Catalog (DataZone) with **100% API coverage** via auto-generation from the botocore service model.

This server automatically generates MCP tools for all 175+ DataZone API operations by reading the service model from botocore at startup. When AWS adds new operations, simply update boto3 — no code changes needed.

## Features

- **100% API coverage**: Every DataZone operation is exposed as an MCP tool
- **Auto-updating**: New operations appear automatically when boto3 is updated
- **Compatible**: Includes all tools from the official `awslabs/amazon-datazone-mcp-server`, plus 126+ more
- **Dual transport**: Supports stdio (local) and Streamable HTTP (remote)
- **Standard AWS credentials**: Uses the standard boto3 credential chain
- **Correct parameter schemas**: Each tool exposes the exact input schema from the AWS API (not a generic kwargs wrapper)

## Installation

```bash
# From source
git clone https://github.com/difeorte/amazon-sagemaker-catalog-mcp-server.git
cd amazon-sagemaker-catalog-mcp-server
pip install .

# For development
pip install -e ".[dev]"
```

## Prerequisites

### AWS Credentials

The server uses the standard boto3 credential chain:

1. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
2. AWS credentials file (`~/.aws/credentials`)
3. AWS SSO config (`~/.aws/config` with `sso_session`)
4. Instance profile (EC2, ECS, Lambda)

### IAM Permissions

The IAM role or user needs DataZone permissions. For a read-only catalog agent (browse, search, subscribe):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "datazone:List*",
        "datazone:Get*",
        "datazone:Search*",
        "datazone:CreateSubscriptionRequest"
      ],
      "Resource": "*"
    }
  ]
}
```

For full access (create/update/delete resources), use `datazone:*` — but scope it down based on your use case. The server exposes all 175+ operations, so the IAM policy is what controls what the agent can actually do.

### SageMaker Unified Studio Domains

For catalog operations like `search_listings`, `create_subscription_request`, etc., the IAM role must be added as a **project member** in the SageMaker Unified Studio portal. This is a one-time setup per role per project. Without project membership, administrative operations (`list_domains`, `get_domain`, `list_projects`) still work, but catalog-level operations will return `AccessDeniedException`.

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `AWS_REGION` | AWS region for API calls | boto3 default |
| `AWS_PROFILE` | AWS profile name | default |
| `MCP_TRANSPORT` | Transport type (`stdio` or `streamable-http`) | `stdio` |
| `MCP_PORT` | Port for HTTP transport | `8000` |

## Usage

### With stdio (local, default)

```bash
sagemaker-catalog-mcp-server
```

### With Streamable HTTP (remote)

```bash
sagemaker-catalog-mcp-server --transport streamable-http --port 8000
```

### CLI Options

```
--transport {stdio,streamable-http}  Transport type (default: stdio)
--port PORT                          Port for HTTP transport (default: 8000)
--region REGION                      AWS region
--profile PROFILE                    AWS profile name
```

### MCP Client Configuration (Kiro, Claude Desktop, etc.)

Add to your MCP client configuration (e.g., `.kiro/settings/mcp.json`):

```json
{
  "mcpServers": {
    "sagemaker-catalog": {
      "command": "sagemaker-catalog-mcp-server",
      "args": ["--region", "us-east-1"],
      "env": {
        "AWS_PROFILE": "your-profile"
      }
    }
  }
}
```

Or if running from source without installing:

```json
{
  "mcpServers": {
    "sagemaker-catalog": {
      "command": "/path/to/project/.venv/bin/python",
      "args": ["-m", "sagemaker_catalog_mcp_server"],
      "env": {
        "AWS_REGION": "us-east-1",
        "AWS_PROFILE": "your-profile",
        "PYTHONPATH": "/path/to/project/src"
      }
    }
  }
}
```

## Available Tools

The server exposes 175+ tools, one for each DataZone API operation. Examples:

| Tool | Description |
|---|---|
| `list_domains` | Lists Amazon DataZone domains |
| `get_domain` | Gets a domain |
| `create_project` | Creates a project |
| `search_listings` | Searches published assets in the catalog |
| `create_subscription_request` | Requests access to a data asset |
| `get_asset` | Gets asset details (technical + business metadata) |
| `create_glossary` | Creates a business glossary |
| `list_data_sources` | Lists data sources in a project |

For the complete list, start the server and use your MCP client's tool listing feature.

## Important Considerations

- **Project membership setup** — To add an IAM role as a project member programmatically, the data domain unit that owns the project must first have the "Add to project member pool" policy enabled by the domain unit owner. Without this policy, the API returns `AccessDeniedException`. Currently, adding project members is done from the SageMaker Unified Studio portal.

- **Tested on SageMaker Catalog** — This server has been tested on SageMaker Catalog (which runs on Amazon DataZone). It has not been tested on standalone DataZone V1 domains.

## Querying Subscribed Data

When a subscription is approved, SageMaker Unified Studio creates resource links in the consumer project's Lakehouse database (e.g., `central_data_lake_<envId>`). To query subscribed data, the agent must chain-assume the project execution role (`datazone_usr_role_<projectId>_<envId>`) and use the project's Athena workgroup. The data appears under the local Lakehouse database, not the producer's catalog ID.

## Compatibility

This server is an unofficial extended version inspired by `awslabs/amazon-datazone-mcp-server` (v0.1.1). All 49 tools from the official server are available with the same names and parameters, plus 126+ additional tools covering the rest of the API.

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest -v
```

## Architecture

The server uses a code generation approach at startup:

1. **ServiceModelParser** reads `service-2.json` from botocore (supports `.json.gz`)
2. **ToolGenerator** creates MCP tool definitions with correct JSON Schema for each operation
3. **ToolExecutor** executes operations against AWS via boto3 with response serialization
4. **Low-level MCP SDK** (`mcp.server.lowlevel.Server`) handles the protocol, ensuring each tool gets its exact `inputSchema` from the AWS API

This means the server automatically supports new API operations when boto3 is updated.

## License

Apache 2.0
