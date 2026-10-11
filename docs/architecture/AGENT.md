# Agent

The investigator (`agents/agent.py`, version `relay-agent-1`) is a LangGraph `StateGraph` with conditional edges between a model node and a tool node. It begins with only the tenant, case, source version and task. Source records are never preloaded into the prompt, so the agent has to decide what to inspect.

## Tools

| Tool | Input | Effect |
| --- | --- | --- |
| `observe_system` | `system`: one of `procurement`, `warehouse`, `billing`, `case_management` | Returns one scoped record with a content-addressed `evidence_id` and `source_version`. Includes a browser capture when evidence pages are enabled. |
| `inspect_document` | `document`: `invoice` or `delivery_note` | Same, for an original source document |
| `record_hypotheses` | 1–3 claims, each `supported`, `contradicted` or `uncertain`, citing 1–6 evidence IDs | Stored as public working memory. Each citation must be unique and observed in this run. |
| `submit_plan` | A strict `Plan` | Validated against policy. Errors come back as bounded tool feedback. |

Each round may issue up to four evidence calls. The two control tools, `submit_plan` and `record_hypotheses`, must be called alone in their round. A plan is accepted only when it cites evidence from all four systems and both documents, follows recorded hypotheses, matches the case scope and source version, and satisfies the declared contract.

The system prompt states that source documents, screenshots and tool values are untrusted data and never instructions. It also states that the agent cannot approve, execute or read evaluation answers. The approve and execute operations are not tools.

## Budgets

| Bound | Value |
| --- | --- |
| Rounds | 12 |
| Output tokens | `min(2048, 12000 − used)` per request |
| Input tokens | 8,000 per request (counted before generation), 64,000 cumulative |
| Estimated spend | $0.50 cumulative (500,000 micro-USD), reserved before each generation |
| Evidence calls | 24 total, at most 3 identical |
| Policy corrections | 2 |
| Active model time | 240 s, enforced with `asyncio.timeout` |
| Generation | 60 s deadline, 30 s SDK timeout, `max_retries=0` |
| Provider request | 2 MB encoded body |
| Graph | `recursion_limit` 40 |

Exceeding any bound ends the run without producing actions. Unknown tools, invented evidence IDs, malformed usage or a mismatched model identity are refused the same way.

## Multimodal evidence

`BrowserEvidence` serves the original source pages from an ephemeral loopback server and renders them in Chromium through Playwright. Request routing aborts everything except `GET` requests to its own origin and read-only page paths. Source strings are HTML-escaped, and a content security policy blocks active content. The agent cannot pass a URL, run JavaScript, click or upload anything.

Each capture records PNG bytes, their SHA-256, the accessibility text and the versioned structured record. The source version is checked before and after capture, and a mismatch rejects the observation. Image blocks are added to provider tool results. `trim_images()` keeps the latest two in context and replaces older ones with a text placeholder, while the original PNGs stay on disk as artifacts.

## Model transport and receipts

`AgentModel` uses `AsyncAnthropic` with typed server-sent events and strict response validation. For each request it:

1. counts input tokens and refuses requests over 8,000;
2. reserves the worst-case cost of the request against the cumulative cap;
3. streams the response and requires `message_stop`;
4. records the typed usage and the exact response as a model receipt before the graph checkpoint commits.

On recovery, a completed receipt that matches the request replays without a new generation. An unknown or changed receipt blocks replay, so an interrupted paid call is never silently repeated. If the provider reports a cost above the estimate, the committed amount rises. Unexpected cache billing marks the receipt unresolved.

## Checkpoints and recovery

`AsyncSqliteSaver` checkpoints the graph state as plain JSON: messages, evidence, hypotheses, counters, calls, activity and plan. `fingerprint()` hashes the package source, the dependency lock, the client mode, the pricing profile and the browser configuration. Recovery requires an exact fingerprint match. Otherwise it is refused rather than migrated. A completed graph can be inspected without any new call, and an interrupted transition resumes with its counters intact.

## Planners

| Planner | Used by | Behavior |
| --- | --- | --- |
| Live agent | Workbench and workers when `RELAY_ALLOW_LIVE=1` | Anthropic tool use over the full loop above |
| `ScriptedAgent` | Workbench default, tests, case matrix | Deterministic client that reads the actual tool replies. With `incorrect_first`, it submits one wrong amount, receives policy feedback and corrects it. |
| `DiagnosticPlanner` | Public demo and uploads | Applies the declared contract to observed quantities inside the `observe → propose → policy → simulate` workflow |
| `AnthropicPlanner` | Comparison path | Single structured planning request under the same token and cost bounds |

[Execution](EXECUTION.md) · [Overview](OVERVIEW.md)
