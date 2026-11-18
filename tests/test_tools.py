"""Each tool end to end: parameters in, Dify messages out, against a scripted Treza."""

import pytest

from tests.test_client import QUOTE, FakeTreza
from tools import client as c
from tools.generate_image import GenerateImageTool
from tools.generate_video import GenerateVideoTool
from tools.get_balance import GetBalanceTool
from tools.get_run import GetRunTool
from tools.run_pipeline import RunPipelineTool

IMAGE = "https://media.trezalabs.com/api/media/generated/image/a.png"
VIDEO = "https://media.trezalabs.com/api/media/generated/video/a.mp4"


def run(tool_cls, fake, params, monkeypatch):
    monkeypatch.setattr(c.time, "sleep", lambda s: None)
    tool = tool_cls.from_credentials({"api_key": "treza_live_test"})
    monkeypatch.setattr(tool, "client", lambda: c.TrezaClient("treza_live_test", session=fake))
    messages = list(tool.invoke(params))
    out = {"text": [], "json": [], "vars": {}, "images": []}
    for m in messages:
        kind = m.type.value
        if kind == "text":
            out["text"].append(m.message.text)
        elif kind == "json":
            out["json"].append(m.message.json_object)
        elif kind == "variable":
            out["vars"][m.message.variable_name] = m.message.variable_value
        elif kind == "image":
            out["images"].append(m.message.text)
    return out


def test_generate_image(monkeypatch):
    fake = FakeTreza(
        make_image=[(200, QUOTE)],
        run_pipeline=[(200, {"runId": "r1"})],
        get_run=[(200, {"status": "success", "outputs": {"image": IMAGE}, "durationMs": 7300})],
    )
    out = run(GenerateImageTool, fake, {"prompt": "a lighthouse at dawn", "max_cost_usd": 0.25, "aspect_ratio": "9:16"}, monkeypatch)
    assert fake.asked("make_image") == [{"prompt": "a lighthouse at dawn", "aspectRatio": "9:16", "maxPriceUsd": 0.25}]
    assert out["vars"]["url"] == IMAGE and out["vars"]["price_usd"] == 0.06 and out["vars"]["finished"] is True
    assert out["vars"]["model"] == "google/gemini-2.5-flash-image" and out["vars"]["run_id"] == "r1"
    assert out["text"] == [f"The picture is ready: {IMAGE} It cost $0.06."]
    assert out["images"] == [IMAGE]
    assert out["json"][0]["render_seconds"] == 7.3



def test_generate_video_without_a_max_cost_runs_at_the_quote(monkeypatch):
    # 0.0.2: Max cost is optional. The old $2 default refused an 8 second Seedance 2.5 clip ($2.63).
    fake = FakeTreza(
        make_video=[(200, {**QUOTE, "estimatedChargeUsd": 2.63, "model": "bytedance/seedance-2.5"})],
        run_pipeline=[(200, {"runId": "r9"})],
        get_run=[(200, {"status": "running", "pollAfterSec": 10})],
    )
    out = run(GenerateVideoTool, fake, {"prompt": "waves", "duration_sec": 8, "wait_seconds": 5}, monkeypatch)
    assert fake.asked("make_video") == [{"prompt": "waves", "durationSec": 8.0}]
    assert fake.asked("run_pipeline") and out["vars"]["price_usd"] == 2.63


def test_generate_video_still_rendering(monkeypatch):
    fake = FakeTreza(
        make_video=[(200, {**QUOTE, "estimatedChargeUsd": 0.56, "model": "google/veo-3.1-lite"})],
        run_pipeline=[(200, {"runId": "r2"})],
        get_run=[(200, {"status": "running", "pollAfterSec": 10})],
    )
    out = run(GenerateVideoTool, fake, {"prompt": "waves", "max_cost_usd": 2, "duration_sec": 8, "with_audio": False, "wait_seconds": 5}, monkeypatch)
    assert fake.asked("make_video") == [{"prompt": "waves", "durationSec": 8.0, "withAudio": False, "maxPriceUsd": 2.0}]
    assert out["vars"]["status"] == "running" and out["vars"]["finished"] is False and out["vars"]["url"] == ""
    assert "still rendering" in out["text"][0] and "run ID r2" in out["text"][0] and "pipeline_1" in out["text"][0]


def test_run_pipeline_with_inputs(monkeypatch):
    fake = FakeTreza(
        estimate_run_cost=[(200, {**QUOTE, "estimatedChargeUsd": 1.2})],
        run_pipeline=[(200, {"runId": "r3"})],
        get_run=[(200, {"status": "success", "outputs": {"final_cut": VIDEO}})],
    )
    out = run(RunPipelineTool, fake, {"pipeline_id": "pipeline_1", "inputs": '{"prompt_1": "a fox"}', "max_cost_usd": 5}, monkeypatch)
    assert fake.asked("run_pipeline")[0]["inputs"] == {"prompt_1": "a fox"}
    assert out["vars"]["url"] == VIDEO and out["vars"]["price_usd"] == 1.2

    with pytest.raises(c.TrezaError, match="Inputs must be JSON"):
        run(RunPipelineTool, FakeTreza(), {"pipeline_id": "pipeline_1", "inputs": "{not json", "max_cost_usd": 5}, monkeypatch)


def test_get_run(monkeypatch):
    fake = FakeTreza(get_run=[(200, {"status": "success", "outputs": {"video": VIDEO}})])
    out = run(GetRunTool, fake, {"pipeline_id": "pipeline_1", "run_id": "r2"}, monkeypatch)
    assert out["vars"]["url"] == VIDEO and out["text"] == [f"The render is ready: {VIDEO}"]


def test_get_balance(monkeypatch):
    fake = FakeTreza(get_credit_balance=[(200, {"balanceUsd": 12.5, "markup": 1.4, "packs": [], "topUpUrl": "https://www.trezalabs.com/platform/settings"})])
    out = run(GetBalanceTool, fake, {}, monkeypatch)
    assert out["vars"]["balance_usd"] == 12.5 and out["text"][0].startswith("Your Treza balance is $12.50.")
    assert out["json"] == [{"balance_usd": 12.5, "top_up_url": "https://www.trezalabs.com/platform/settings"}]
