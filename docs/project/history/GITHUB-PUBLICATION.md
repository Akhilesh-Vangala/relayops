> Historical record. [Current project overview](../../../README.md) and [current handoff](../HANDOFF.md) take precedence.

# GitHub publication and verified CI

Public repository: [Akhilesh-Vangala/relayops](https://github.com/Akhilesh-Vangala/relayops), default branch `main`. Published October 13, 2026 following the user's request to present both flagships on GitHub. This repository contains only the original RelayOps project; workspace career planning, the personal portfolio folder and private/generated runtime files are excluded.

## Recorded publication baseline

The existing local history was preserved:

- `b41cbad` — original governed workflow foundation.
- `dc85c15` — checkpointed multimodal agent and operator workbench.
- `52343c9` — reproducible locked-dependency CI.
- [`7aa02f7`](https://github.com/Akhilesh-Vangala/relayops/commit/7aa02f7c74cca3c1826f612e83b378a957fd1751) — visual architecture and operator evidence.

[Actual Actions run 38345763992](https://github.com/Akhilesh-Vangala/relayops/actions/runs/38345763992) succeeded for the exact publication commit. Both jobs used fresh Ubuntu runners and Python 3.11.17 with the hash-verified dependency lock and real Chromium installation.

| Job | Verified evidence |
| --- | --- |
| Protocol, policy and recovery | Dependency compatibility passes; 47 unit/integration tests pass; all 12 known scripted matrix assessments pass with original business state untouched. |
| Operator and browser evidence journey | 16 actual browser journey checks pass, including six captures, proposal correction, exact-version review, execution/repeated-request checks and responsive monochrome pages. |

Downloaded Actions artifacts and logs were inspected to confirm these counts. The matrix declares zero live model generations and scripted integration scope. The browser report declares no live model generation. Artifacts are retained for 14 days; the workflow and reproduction commands remain in Git.

## Presentation and structure

Original monochrome banner and system map; actual read-only app captures; detailed agent flow; documentation index; source/tradeoff guide; contribution expectations; focused bug/proposal/PR templates; clear current evidence and remaining release gates.

GitHub's Markdown API rendered the README successfully, retaining its Mermaid block, details sections and all image references. The full published file tree was compared with local Git blob hashes; README/diagram previews were checked at desktop and mobile widths. Credential-signature scanning covered history and owned files; `.env`, environments, tooling and generated runtime remain ignored. These checks are publication hygiene, not a security certification.

## Practical limits

The CI badge tracks the current branch. The run above is a recorded baseline, not a promise that future commits pass. No live model accuracy, frozen held-out score, actual customer benefit, production side effect, Docker runtime or cloud hosting is established by publication.

See [current agent implementation](../../architecture/AGENT-WORKBENCH.md), [design tradeoffs](../../development/REPOSITORY.md), [evaluation scope](../../evaluation/README.md) and [release gates](../PLAN.md).
