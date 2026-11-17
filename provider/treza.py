from typing import Any

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

from tools.client import TrezaClient, TrezaError


class TrezaProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        """The key works if Treza says whose account it opens."""
        api_key = str(credentials.get("api_key") or "").strip()
        if not api_key:
            raise ToolProviderCredentialValidationError("Add your Treza API key.")
        try:
            TrezaClient(api_key).call("get_profile")
        except TrezaError as err:
            raise ToolProviderCredentialValidationError(str(err)) from err
        except Exception as err:
            raise ToolProviderCredentialValidationError(f"Could not reach Treza: {err}") from err
