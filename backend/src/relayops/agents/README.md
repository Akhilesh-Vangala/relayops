# agents

LangGraph investigator, model transport, browser evidence and planners. Nothing here can approve or execute an action.

- [agent.py](agent.py): `StateGraph` investigator, tools, budgets, corrections and checkpoints
- [agent_transport.py](agent_transport.py): `AsyncAnthropic` streaming, token counting, cost reservation and model receipts
- [browser.py](browser.py): loopback-only Playwright captures of source pages
- [planner.py](planner.py): `DiagnosticPlanner` and the single-request `AnthropicPlanner`
- [scripted_agent.py](scripted_agent.py): deterministic client for tests and the case matrix
- [workflow.py](workflow.py): `observe → propose → policy → simulate` graph and `simulate_plan()`

[Agent design](../../../../docs/architecture/AGENT.md)
