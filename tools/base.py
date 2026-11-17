"""What every Treza tool shares: the client, and how a render is reported back."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

from tools.client import Data, TrezaClient, TrezaError, finished_or_raise, run_item, to_number

# The variables a render tool declares in its output_schema.
RENDER_VARIABLES = ("url", "status", "finished", "price_usd", "model", "run_id", "pipeline_id")


class TrezaTool:
    """Mixed into each tool next to dify_plugin.Tool (one Tool subclass per file)."""

    def client(self) -> TrezaClient:
        return TrezaClient(str(self.runtime.credentials.get("api_key") or ""))

    def wait_seconds(self, tool_parameters: dict[str, Any], default: float, most: float = 540) -> float:
        value = to_number(tool_parameters.get("wait_seconds"))
        return min(max(default if value is None else value, 0), most)

    def report(
        self,
        run: Data,
        *,
        noun: str,
        output_key: str | None = None,
        extra: Data | None = None,
        show_image: bool = False,
    ) -> Generator[ToolInvokeMessage, None, None]:
        """Send a render back as JSON, a sentence, named variables and, for a picture, the picture."""
        finished_or_raise(run)
        item = run_item(run, output_key, extra)
        yield self.create_json_message(item)
        for name in RENDER_VARIABLES:
            yield self.create_variable_message(name, item.get(name, "" if name not in ("finished", "price_usd") else None))
        price = item.get("price_usd")
        cost = f" It cost ${price:.2f}." if isinstance(price, (int, float)) else ""
        if item.get("url"):
            yield self.create_text_message(f"The {noun} is ready: {item['url']}{cost}")
            if show_image:
                yield self.create_image_message(item["url"])
        elif item["status"] == "running":
            yield self.create_text_message(
                f"The {noun} is still rendering.{cost} Use Check a Render with run ID {item.get('run_id')} "
                f"and pipeline ID {item.get('pipeline_id')} to get the file when it is done."
            )
        else:
            yield self.create_text_message(f"The render finished with status {item['status']} and no file.{cost}")


def quote_summary(started: Data) -> Data:
    """Price and model from the quote, for the result."""
    quoted = started.get("quoted") or {}
    model = quoted.get("model")
    return {
        "price_usd": started.get("priceUsd"),
        "model": model.get("id") if isinstance(model, dict) else model,
        "duration_sec": quoted.get("durationSec"),
        "aspect_ratio": quoted.get("aspectRatio"),
    }


__all__ = ["TrezaTool", "TrezaError", "quote_summary"]
