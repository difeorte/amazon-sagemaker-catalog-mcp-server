"""Fixtures compartidos para tests del SageMaker Catalog MCP Server."""

import pytest


@pytest.fixture
def minimal_service_model():
    """Service model mínimo con 2 operaciones para testing."""
    return {
        "version": "2.0",
        "metadata": {
            "apiVersion": "2018-05-10",
            "endpointPrefix": "datazone",
            "jsonVersion": "1.1",
            "protocol": "rest-json",
            "serviceFullName": "Amazon DataZone",
            "serviceId": "DataZone",
            "signatureVersion": "v4",
            "signingName": "datazone",
            "uid": "datazone-2018-05-10",
        },
        "operations": {
            "ListDomains": {
                "name": "ListDomains",
                "http": {"method": "GET", "requestUri": "/v2/domains"},
                "input": {"shape": "ListDomainsInput"},
                "output": {"shape": "ListDomainsOutput"},
                "documentation": "<p>Lists Amazon DataZone domains.</p>",
            },
            "GetDomain": {
                "name": "GetDomain",
                "http": {"method": "GET", "requestUri": "/v2/domains/{identifier}"},
                "input": {"shape": "GetDomainInput"},
                "output": {"shape": "GetDomainOutput"},
                "documentation": "<p>Gets an Amazon DataZone domain.</p>",
            },
        },
        "shapes": {
            "ListDomainsInput": {
                "type": "structure",
                "members": {
                    "maxResults": {
                        "shape": "MaxResults",
                        "documentation": "<p>Max results.</p>",
                    },
                    "nextToken": {
                        "shape": "PaginationToken",
                        "documentation": "<p>Pagination token.</p>",
                    },
                    "status": {
                        "shape": "DomainStatus",
                        "documentation": "<p>Status filter.</p>",
                    },
                },
            },
            "ListDomainsOutput": {
                "type": "structure",
                "required": ["items"],
                "members": {
                    "items": {
                        "shape": "DomainSummaries",
                        "documentation": "<p>The results.</p>",
                    },
                    "nextToken": {
                        "shape": "PaginationToken",
                        "documentation": "<p>Next page token.</p>",
                    },
                },
            },
            "GetDomainInput": {
                "type": "structure",
                "required": ["identifier"],
                "members": {
                    "identifier": {
                        "shape": "DomainId",
                        "documentation": "<p>The domain identifier.</p>",
                    },
                },
            },
            "GetDomainOutput": {
                "type": "structure",
                "required": ["id", "name", "status"],
                "members": {
                    "id": {
                        "shape": "DomainId",
                        "documentation": "<p>The domain ID.</p>",
                    },
                    "name": {
                        "shape": "DomainName",
                        "documentation": "<p>The domain name.</p>",
                    },
                    "status": {
                        "shape": "DomainStatus",
                        "documentation": "<p>The domain status.</p>",
                    },
                    "description": {
                        "shape": "Description",
                        "documentation": "<p>The description.</p>",
                    },
                    "tags": {
                        "shape": "Tags",
                        "documentation": "<p>The tags.</p>",
                    },
                },
            },
            "MaxResults": {"type": "integer", "max": 50, "min": 1},
            "PaginationToken": {"type": "string", "max": 8192, "min": 1},
            "DomainId": {"type": "string"},
            "DomainName": {"type": "string", "max": 64, "min": 1},
            "Description": {"type": "string", "max": 2048},
            "DomainStatus": {
                "type": "string",
                "enum": [
                    "CREATING",
                    "AVAILABLE",
                    "CREATION_FAILED",
                    "DELETING",
                    "DELETED",
                    "DELETION_FAILED",
                ],
            },
            "DomainSummaries": {
                "type": "list",
                "member": {"shape": "DomainSummary"},
            },
            "DomainSummary": {
                "type": "structure",
                "required": ["id", "name", "status"],
                "members": {
                    "id": {"shape": "DomainId"},
                    "name": {"shape": "DomainName"},
                    "status": {"shape": "DomainStatus"},
                },
            },
            "Tags": {
                "type": "map",
                "key": {"shape": "TagKey"},
                "value": {"shape": "TagValue"},
            },
            "TagKey": {"type": "string"},
            "TagValue": {"type": "string"},
        },
    }
