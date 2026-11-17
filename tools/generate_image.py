from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools.base import TrezaTool, quote_summary
from tools.client import compact, max_cost


class GenerateImageTool(TrezaTool, Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        client = self.client()
        cap = max_cost(tool_parameters.get("max_cost_usd"))
        args = compact(
            {
                "prompt": tool_parameters.get("prompt"),
                "aspectRatio": tool_parameters.get("aspect_ratio"),
                "model": tool_parameters.get("model"),
                "name": tool_parameters.get("name"),
                "maxPriceUsd": cap,
            }
        )
        started = client.start_quoted(cap, lambda: client.request("make_image", args))
        run = client.wait_for_run(started["pipelineId"], started["runId"], self.wait_seconds(tool_parameters, 120))
        run = {"runId": started["runId"], "pipelineId": started["pipelineId"], **run}
        yield from self.report(run, noun="picture", output_key="image", extra=quote_summary(started), show_image=True)
