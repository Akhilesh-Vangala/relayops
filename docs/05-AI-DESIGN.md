# AI design

Current LangGraph is a bounded assessment workflow with fixed observation collection and one proposal call. Known DiagnosticPlanner knows the contract and is a reproducibility baseline, not AI intelligence. AnthropicPlanner uses official AsyncAnthropic typed streaming and a forced submit_plan schema; no live generation has run.

The model sees public observations and rules. It cannot approve original-world writes or read private evaluation answers. Strict Pydantic rejects extra fields, coercion and unknown action kinds. Policy validation does not make a model explanation true; independent final-state checks remain outside its proposal.

Live admission: explicit RELAY_ALLOW_LIVE=1/private key/model matching a trusted profile; active model and input counting before generation;8000input/2048output/60seconds;$0.25estimated allowance; zero automatic generation retries. One persisted receipt blocks a second generation on the same run even after unknown failure. Complete reported usage is saved even when plan validation fails. Local fake-SDK tests verify application behavior, not official HTTP transport or model quality. Price profile was checked against official rates; estimates are not invoice caps.

Next: a bounded observation→decision→action→postcondition loop; multimodal grounding; evidence conflict handling; selective clarification; public working memory; changing-world updates; controlled API-vs-browser routing; actual provider-transport tests and early live evaluation. Add specialized document or browser workers only when an ablation demonstrates value. Persist recovery through one business lifecycle authority.
