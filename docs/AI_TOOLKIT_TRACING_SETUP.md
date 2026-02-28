# AI Toolkit + Agent Inspector Tracing Setup

This project is wired for OpenTelemetry tracing with Agent Framework and VS Code AI Toolkit.

## What is configured in code

- `server.py` configures tracing with:
  - `configure_otel_providers(vs_code_extension_port=4317, enable_sensitive_data=True)`
- `app.py` and `main.py` now enable tracing only when:
  - `AITK_TRACING_ENABLED=1`

This prevents generation failures when the local collector/inspector is not running.

## Why this change

Based on Microsoft Learn:

- `configure_otel_providers()` should be called once at startup.
- VS Code integration uses the local extension endpoint/port (`4317` by default).
- Local tracing in VS Code is intended to run with AI Toolkit collector/inspector active.

## Run with Agent Inspector (recommended)

Use the existing VS Code tasks in this repo:

1. Run task: **Validate prerequisites**
2. Run task: **Run Agent HTTP Server**
3. Run task: **Open Agent Inspector**

The HTTP server runs with `agentdev` + `debugpy` and is trace-ready.

## Enable tracing in Streamlit app / CLI

For `app.py` and `main.py`, tracing is opt-in:

- PowerShell:

```powershell
$env:AITK_TRACING_ENABLED="1"
python -m streamlit run app.py
```

or:

```powershell
$env:AITK_TRACING_ENABLED="1"
python main.py
```

If not set, tracing is skipped to avoid websocket/collector startup errors.

## Optional OTEL environment variables

You can also configure standard OTEL variables (if needed):

- `OTEL_EXPORTER_OTLP_ENDPOINT`
- `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`
- `OTEL_EXPORTER_OTLP_PROTOCOL`
- `ENABLE_CONSOLE_EXPORTERS`

## References (Microsoft Learn)

- Agent Framework observability API (`configure_otel_providers`)
- Foundry tracing setup and AI Toolkit local tracing guidance
- Trace locally with AI Toolkit in VS Code
