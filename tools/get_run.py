from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools.base import TrezaTool
from tools.client import TrezaError


class GetRunTool(TrezaTool, Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        pipeline_id = str(tool_parameters.get("pipeline_id") or "").strip()
        run_id = str(tool_parameters.get("run_id") or "").strip()
        if not pipeline_id or not run_id:
            raise TrezaError("Add both the Pipeline ID and the Run ID. The step that started the render returns them.")
        run = self.client().wait_for_run(pipeline_id, run_id, self.wait_seconds(tool_parameters, 0))
        run = {"runId": run_id, "pipelineId": pipeline_id, **run}
        yield from self.report(run, noun="render")
