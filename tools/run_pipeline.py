import json
from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools.base import TrezaTool
from tools.client import TrezaError, max_cost


class RunPipelineTool(TrezaTool, Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        client = self.client()
        cap = max_cost(tool_parameters.get("max_cost_usd"))
        pipeline_id = str(tool_parameters.get("pipeline_id") or "").strip()
        if not pipeline_id:
            raise TrezaError("Add the Pipeline ID. It is in the pipeline's address in Treza and starts with pipeline_.")
        inputs = None
        raw = tool_parameters.get("inputs")
        if isinstance(raw, str) and raw.strip():
            try:
                inputs = json.loads(raw)
            except ValueError as err:
                raise TrezaError('Inputs must be JSON, for example {"prompt_1": "a lighthouse at dawn"}.') from err
            if not isinstance(inputs, dict):
                raise TrezaError('Inputs must be a JSON object with one entry per input step, for example {"prompt_1": "a lighthouse at dawn"}.')
        started = client.start_quoted(cap, lambda: client.request("estimate_run_cost", {"pipelineId": pipeline_id}), inputs or None)
        run = client.wait_for_run(started["pipelineId"], started["runId"], self.wait_seconds(tool_parameters, 300))
        run = {"runId": started["runId"], "pipelineId": started["pipelineId"], **run}
        yield from self.report(run, noun="render", extra={"price_usd": started.get("priceUsd")})
