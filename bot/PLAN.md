# Bot Development Plan

This bot should be built around a transport-independent handler layer so we can test command behavior without depending on Telegram. The core rule is simple: handlers receive plain Python input, call services, and return plain text output. Telegram should only be a delivery mechanism around that logic. That gives us two entry points that share the same behavior: a real Telegram polling mode for users and a `--test` CLI mode for local verification and autochecking.

The first step is the scaffold. We need a `bot.py` entry point, a `handlers/` package, a `services/` package, and a configuration module that reads `.env.bot.secret` without requiring `BOT_TOKEN` in test mode. The entry point should parse CLI arguments, load settings, construct services, and then either run a direct handler call in test mode or start the Telegram bot in polling mode. This keeps startup logic explicit and easy to debug.

The second step is backend integration. A small LMS client should wrap HTTP calls to the backend using `httpx`, attach the API key, and expose methods like `get_health()`, `list_labs()`, and `get_scores(lab)`. Handlers will depend on that client through a small service container, which makes replacing or mocking it straightforward in future tests.

The third step is command and intent routing. We should support explicit slash commands such as `/start`, `/help`, `/health`, `/labs`, and `/scores lab-04`. Later, free-form text such as "what labs are available" can be routed through an intent layer backed by the LLM client or a lightweight rule-based fallback. The routing logic should stay in the handler layer, not in Telegram callbacks, so CLI test mode exercises the same path.

The fourth step is quality and deployment. We should verify `uv sync`, run `uv run bot.py --test "/start"`, and confirm that every supported command prints a non-empty response and exits successfully. After that, deployment on the VM should follow the existing project pattern: fill `.env.bot.secret`, run the bot with `uv`, check logs, and confirm Telegram responses. This structure leaves room for future unit tests and richer features without rewriting the transport layer.
