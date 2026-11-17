from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools.base import TrezaTool
from tools.client import TOP_UP_URL, to_number


class GetBalanceTool(TrezaTool, Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        balance = self.client().call("get_credit_balance")
        usd = to_number(balance.get("balanceUsd"))
        yield self.create_json_message(balance)
        yield self.create_variable_message("balance_usd", usd)
        if usd is None:
            yield self.create_text_message("Treza did not report a balance.")
        else:
            yield self.create_text_message(f"Your Treza balance is ${usd:.2f}. Add credits at {balance.get('topUpUrl') or TOP_UP_URL}")
