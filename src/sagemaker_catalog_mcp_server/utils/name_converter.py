"""Conversión de nombres PascalCase ↔ snake_case."""

import re


class NameConverter:
    """Convierte nombres entre PascalCase (API de AWS) y snake_case (tools MCP)."""

    # Patrón para insertar _ antes de transiciones de minúscula/dígito a mayúscula
    # y entre acrónimos y palabras (ej: IAMPolicy → IAM_Policy)
    _PASCAL_TO_SNAKE_RE = re.compile(
        r"(?<=[a-z0-9])(?=[A-Z])"  # minúscula/dígito seguido de mayúscula
        r"|(?<=[A-Z])(?=[A-Z][a-z])"  # acrónimo seguido de palabra (IAMPolicy → IAM_Policy)
    )

    @staticmethod
    def to_snake_case(pascal_name: str) -> str:
        """Convierte PascalCase a snake_case.

        Ejemplos:
            ListDomains → list_domains
            GetIAMPolicy → get_iam_policy
            CreateAssetType → create_asset_type
            GetIAMPortalLoginUrl → get_iam_portal_login_url
        """
        result = NameConverter._PASCAL_TO_SNAKE_RE.sub("_", pascal_name)
        return result.lower()

    @staticmethod
    def to_pascal_case(snake_name: str) -> str:
        """Convierte snake_case a PascalCase.

        Ejemplos:
            list_domains → ListDomains
            get_iam_policy → GetIamPolicy
            create_asset_type → CreateAssetType
        """
        return "".join(word.capitalize() for word in snake_name.split("_"))
