"""The quote, cap, start and wait order, against a scripted Treza."""

import pytest

from tools import client as c


class FakeResponse:
    def __init__(self, status, body):
        self.status_code = status
        self._body = body
        self.text = str(body)

    def json(self):
        return self._body


class FakeTreza:
    """Answers each tool from a queue and records what was asked."""

    def __init__(self, **answers):
        self.answers = {tool: list(replies) for tool, replies in answers.items()}
        self.calls = []

    def post(self, url, json=None, headers=None, timeout=None):
        tool = url.rsplit("/", 1)[-1]
        self.calls.append((tool, json, headers))
        status, body = self.answers[tool].pop(0)
        return FakeResponse(status, body)

    def asked(self, tool):
        return [args for name, args, _ in self.calls if name == tool]


QUOTE = {"pipelineId": "pipeline_1", "quoteId": "q1", "estimatedChargeUsd": 0.06, "sufficient": True, "model": {"id": "google/gemini-2.5-flash-image"}}


def client(fake):
    return c.TrezaClient("treza_live_test", session=fake)


def test_quote_then_run_at_the_quoted_price():
    fake = FakeTreza(make_image=[(200, QUOTE)], run_pipeline=[(200, {"runId": "r1"})])
    t = client(fake)
    started = t.start_quoted(0.25, lambda: t.request("make_image", {"prompt": "a lighthouse", "maxPriceUsd": 0.25}))
    assert started["runId"] == "r1" and started["priceUsd"] == 0.06
    assert fake.asked("run_pipeline") == [{"pipelineId": "pipeline_1", "quoteId": "q1"}]
    _, _, headers = fake.calls[0]
    assert headers["Authorization"] == "Bearer treza_live_test"
    assert headers["User-Agent"].startswith("treza-dify/")


def test_over_the_cap_starts_nothing():
    fake = FakeTreza(make_video=[(200, {**QUOTE, "estimatedChargeUsd": 3.2})], run_pipeline=[])
    t = client(fake)
    with pytest.raises(c.TrezaError) as err:
        t.start_quoted(2, lambda: t.request("make_video", {"prompt": "x"}))
    assert "costs $3.20, over the Max cost of $2.00" in str(err.value)
    assert "Nothing was spent" in str(err.value)
    assert fake.asked("run_pipeline") == []


def test_treza_refusing_over_budget_reads_the_same():
    fake = FakeTreza(make_image=[(400, {"code": "OVER_BUDGET", "estimatedChargeUsd": 0.06, "error": "agent-facing text"})])
    t = client(fake)
    with pytest.raises(c.TrezaError) as err:
        t.start_quoted(0.01, lambda: t.request("make_image", {"prompt": "x"}))
    assert "costs $0.06, over the Max cost of $0.01" in str(err.value)
    assert "agent-facing" not in str(err.value)


def test_low_balance_starts_nothing():
    fake = FakeTreza(make_image=[(200, {**QUOTE, "sufficient": False, "balanceUsd": 0.02})], run_pipeline=[])
    t = client(fake)
    with pytest.raises(c.TrezaError) as err:
        t.start_quoted(1, lambda: t.request("make_image", {"prompt": "x"}))
    assert "balance is $0.02" in str(err.value) and "Add credits at" in str(err.value)
    assert fake.asked("run_pipeline") == []


def test_stale_quote_is_quoted_again():
    fake = FakeTreza(
        make_image=[(200, QUOTE), (200, {**QUOTE, "quoteId": "q2"})],
        run_pipeline=[(409, {"code": "STALE_QUOTE", "error": "stale"}), (200, {"runId": "r2"})],
    )
    t = client(fake)
    started = t.start_quoted(0.25, lambda: t.request("make_image", {"prompt": "x"}))
    assert started["runId"] == "r2"
    assert [a["quoteId"] for a in fake.asked("run_pipeline")] == ["q1", "q2"]


def test_price_change_runs_once_under_the_cap_and_never_over_it():
    fake = FakeTreza(
        estimate_run_cost=[(200, {**QUOTE, "estimatedChargeUsd": 1.0})],
        run_pipeline=[(409, {"code": "PRICE_CHANGED", "estimatedChargeUsd": 1.5}), (200, {"runId": "r3"})],
    )
    t = client(fake)
    started = t.start_quoted(2, lambda: t.request("estimate_run_cost", {"pipelineId": "pipeline_1"}), {"prompt_1": "x"})
    assert started["priceUsd"] == 1.5
    second = fake.asked("run_pipeline")[1]
    assert "quoteId" not in second and second["requestId"] and second["inputs"] == {"prompt_1": "x"}

    fake = FakeTreza(
        estimate_run_cost=[(200, {**QUOTE, "estimatedChargeUsd": 1.0})],
        run_pipeline=[(409, {"code": "PRICE_CHANGED", "estimatedChargeUsd": 2.5})],
    )
    t = client(fake)
    with pytest.raises(c.TrezaError) as err:
        t.start_quoted(2, lambda: t.request("estimate_run_cost", {"pipelineId": "pipeline_1"}))
    assert "over the Max cost" in str(err.value)
    assert len(fake.asked("run_pipeline")) == 1


def test_wait_returns_the_finished_run(monkeypatch):
    monkeypatch.setattr(c.time, "sleep", lambda s: None)
    fake = FakeTreza(get_run=[(200, {"status": "running", "pollAfterSec": 2}), (200, {"status": "success", "outputs": {"image": "https://media.trezalabs.com/a.png"}, "durationMs": 6600})])
    run = client(fake).wait_for_run("pipeline_1", "r1", 60)
    item = c.run_item({"runId": "r1", "pipelineId": "pipeline_1", **run}, "image", {"price_usd": 0.06})
    assert item["url"] == "https://media.trezalabs.com/a.png"
    assert item["finished"] is True and item["render_seconds"] == 6.6 and item["price_usd"] == 0.06


def test_no_wait_checks_once_and_reports_running():
    fake = FakeTreza(get_run=[(200, {"status": "running", "pollAfterSec": 5})])
    run = client(fake).wait_for_run("pipeline_1", "r1", 0)
    item = c.run_item({"runId": "r1", "pipelineId": "pipeline_1", **run})
    assert item["status"] == "running" and item["finished"] is False and "url" not in item
    assert len(fake.asked("get_run")) == 1


def test_a_broken_render_stops_with_the_reason():
    run = {"status": "error", "pipelineId": "pipeline_1", "nodes": [{"label": "Video", "error": "The model refused the prompt."}]}
    with pytest.raises(c.TrezaError) as err:
        c.finished_or_raise(run)
    assert "Video: The model refused the prompt." in str(err.value)
    assert "platform/pipelines/pipeline_1" in str(err.value)


def test_refusals_say_what_to_do():
    assert "API key" in str(c.refusal(401, {"error": "Invalid API key."}))
    assert "Add credits at" in str(c.refusal(402, {"error": "Not enough credits."}))
    assert "Wait 30 seconds" in str(c.refusal(429, {"error": "Too many requests.", "retryAfterSec": 30}))


def test_max_cost_is_optional():
    assert c.max_cost("0.25") == 0.25
    # Left empty (or not a positive number) there is no cap, and none is sent to Treza.
    for empty in (None, "", 0, -1, "abc"):
        assert c.max_cost(empty) == float("inf")
    assert c.price_limit(c.max_cost("")) is None
    assert c.price_limit(c.max_cost(3)) == 3
