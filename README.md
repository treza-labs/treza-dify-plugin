# Treza for Dify

Generate AI pictures and videos inside your Dify apps, agents and workflows, and run your own [Treza](https://www.trezalabs.com) pipelines. Treza quotes the price of every render first. Set a **Max cost** and, if the price is over it, the step stops and nothing is spent.

Source: https://github.com/treza-labs/treza-dify-plugin

## What Treza makes

![Four short clips made with Treza: a red hover car racing through a neon city, an astronaut walking over a Martian dune at sunset, an orchid mantis on a leaf, and espresso pouring into a cup](https://raw.githubusercontent.com/treza-labs/treza-labs/main/assets/treza-demo.gif)

These clips were made with [Treza](https://www.trezalabs.com), and the [Dify integration page](https://www.trezalabs.com/integrations/dify) shows how to set up this plugin.

## Tools

| Tool | What it does | Cost |
| --- | --- | --- |
| **Generate an Image** | Makes a picture from a prompt and returns the image and its link. | Uses your Treza credits |
| **Generate a Video** | Makes a short video clip from a prompt and returns a link to the MP4. | Uses your Treza credits |
| **Run a Pipeline** | Runs one of your saved Treza pipelines, with new inputs if you want. | Uses your Treza credits |
| **Check a Render** | Looks up a render by its run ID and returns the file, or its status. | Free |
| **Check Balance** | Shows the credits left on your Treza account. | Free |

## Setup

1. Create a Treza account at https://www.trezalabs.com and add credits. Renders are paid from your Treza credits. The plugin itself is free.
2. Create an API key at https://www.trezalabs.com/platform/api-keys with the `pipelines:read`, `pipelines:write` and `pipelines:run` permissions.
3. In Dify, install **Treza** from the Marketplace, open **Tools > Treza**, choose **Authorize** and paste the key. Dify checks the key against your Treza account before saving it.

## Usage

**In a workflow or chatflow:** add a Treza tool node, and fill in the prompt. **Max cost (USD)** is optional: set it to cap what the step may spend. The node returns these variables for later nodes:

| Variable | Meaning |
| --- | --- |
| `url` | Link to the finished file |
| `status` | `running`, `success`, `partial`, `error` or `cancelled` |
| `finished` | `true` once the render is done |
| `price_usd` | The price Treza quoted |
| `model` | The model that made it |
| `run_id`, `pipeline_id` | IDs for **Check a Render** |

**In an agent:** enable the tools you want. The agent writes the prompt and picks the shape and length. **Max cost**, the model and the wait time are settings you fill in, so the agent cannot raise a spending cap you set. With Max cost left empty an agent can spend up to your Treza balance, so set one on tools you give to an agent.

**Long renders:** pictures usually finish in under 30 seconds and videos in one to five minutes. Each render tool waits up to **Wait (seconds)** for the file. If the render is not done by then, the tool returns `status: running` with the `run_id` and `pipeline_id`. Pass those to **Check a Render** to get the file.

**Run a Pipeline inputs:** leave **Inputs (JSON)** empty to run the pipeline as saved, or pass one entry per input step ID, for example `{"prompt_1": "a lighthouse at dawn"}`. The pipeline ID is in the pipeline's address in Treza and starts with `pipeline_`.

## Errors you may see

- *This render costs $X, over the Max cost of $Y. Nothing was spent.* Raise Max cost, or ask for a shorter clip or a cheaper model.
- *This render costs $X and your Treza balance is $Y.* Add credits in Treza under Settings.
- *Check the Treza API key in this plugin's settings.* The key was deleted or lacks a permission. Create a new one and authorize again.

## Connection requirements

The plugin calls Treza's API over HTTPS at `www.trezalabs.com`. Finished files are served from `media.trezalabs.com`. It makes no other network requests.

## Privacy

See [PRIVACY.md](PRIVACY.md). In short: the plugin sends your prompts and settings to Treza with your API key, and stores nothing itself.

## Support

- Guide: https://www.trezalabs.com/integrations/dify
- Issues: https://github.com/treza-labs/treza-dify-plugin/issues
- Email: hello@trezalabs.com

## Development

```bash
uv sync
uv run pytest
```

Licensed under the MIT License.
