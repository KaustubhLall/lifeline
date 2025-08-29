- Add a new frontend mode that calls this endpoint and shows intermediate tool calls.

## 6. Troubleshooting

- Missing API key: Export one of OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.
- Tool discovery failure: Ensure math_server.py is executable with current Python.
- Windows newline issues: Use `python` not `py` if environment misconfigured.

## 7. Clean Up

Processes are short-lived; no persistent server remains after each run.

---
This demo is isolated from Gmail integration and safe to experiment with before wiring into the main application.

