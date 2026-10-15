# Public app verification — October14,2026

[Working app](https://relayops-two.vercel.app/demo) · [Continuous recording](https://relayops-two.vercel.app/demo/recording) · [Implementation PR5](https://github.com/Akhilesh-Vangala/relayops/pull/5)

The protected implementation is merged at2683b8efffe83eda12b2fd8ebb96b98e16ad89a7. All three required PR checks passed, including actual PostgreSQL, Docker, Compose and Kind. Vercel production deploymentdpl_5yrcQZf88Cfz8uLsJAYFcpSHwx6o serves the canonical public alias.

Actual Chromium execution against that public URL passes investigation→checked approval→lost acknowledgment→reconciliation→independent final-state checks, with four confirmed receipts. Report export, reload/history, cross-browser scope, mobile layout and the native recording player pass with no page errors. The video metadata test now uses a JavaScript function rather than string evaluation so it respects the deployed CSP; the policy is unchanged.

Continuous WebM SHA256: `081c361a9ddf0ebda3cabf755c61128411d65c98aad7ffbc85b6e5faa6b1a393`. [Source/capture manifest](demos/interactive-recording.json). The inline GIF is a separate preview, not the continuous video. Existing private recordings remain available.

The follow-up changes only verification code and documentation. Subsequent GitHub commits redeploy the same application/media source; the current-main workflow badge shows their own CI outcome. Workspace completion evidence records final main/CI/alias identity and downloaded artifacts.

This verifies a real guided synthetic application. It does not establish live model quality, globally durable review/execution, monitored persistent cloud operation or actual-user feedback. No paid model calls were made. [Architecture and replay boundaries](14-INTERACTIVE-PUBLIC-DEMO.md).
