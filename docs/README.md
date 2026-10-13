# RelayOps technical documentation

Start with the [project README](../README.md) for the problem, actual app screenshots, system map and quick start. The project is a local development release; scripted integration evidence does not establish live model quality.

## Review paths

Start with the [engineering case study](CASE-STUDY.md) and [recorded demo](DEMO.md) for a concise review of the business problem, owned contribution, failure behavior and evidence.

| Question | Read |
| --- | --- |
| What problem does this solve? | [Business brief](01-PROJECT-BRIEF.md), [source data and supported contract](04-DATA-AND-INTEGRATIONS.md) |
| Where is the owned agent implementation? | [Current agent and workbench](09-AGENT-AND-WORKBENCH.md), [source map and tradeoffs](10-REPOSITORY-GUIDE.md) |
| How are actions checked and authorized? | [Project flow](03-PROJECT-FLOW.md), [architecture](02-ARCHITECTURE.md), [design decisions](DECISIONS.md) |
| What do the tests actually establish? | [Evaluation](06-EVALUATION.md), [current evidence](../README.md#engineering-evidence), [CI](../.github/workflows/checks.yml), [verified publication](11-GITHUB-PUBLICATION.md) |
| How do I run or inspect the app? | [Public read-only showcase](https://relayops-two.vercel.app), [Vercel boundary](12-VERCEL-SHOWCASE.md), [quick start](../README.md#run-locally), [setup](07-SETUP-AND-DEPLOYMENT.md) |
| What is implemented versus proposed? | [Plan](../PLAN.md), [progress](../PROGRESS.md), [handoff](../HANDOFF.md) |
| Which research informed the design? | [Primary references](REFERENCES.md), [AI design](05-AI-DESIGN.md) |

## Visuals and demo

- [System map](assets/relayops-architecture.svg): read-only model tools, runtime checks, operator review, controlled actions and recovery.
- [Workbench overview](assets/workbench-overview.png) and [investigation](assets/investigation.png): actual read-only captures with original synthetic data and scripted model choices.
- [Complete investigation](assets/investigation-full.png): evidence viewer, public memory and private-copy checks.
- [Visual provenance and review guide](10-REPOSITORY-GUIDE.md).

The source map and current agent document describe the latest implementation. Dated foundation sections in earlier documents are retained as history and explicitly superseded where implementation has advanced. The original [foundation README](../README-HISTORY.md) is preserved.

For repository development, use the [branch, PR and release policy](../BRANCHING.md).
