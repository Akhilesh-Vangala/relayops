async function post(path, value) {
  const response = await fetch(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": crypto.randomUUID(),
    },
    body: JSON.stringify(value),
  });
  const result = await response.json();
  if (!response.ok)
    throw new Error(
      typeof result.detail === "string"
        ? result.detail
        : JSON.stringify(result.detail),
    );
  return result;
}
document.querySelectorAll("[data-start]").forEach((button) =>
  button.addEventListener("click", async () => {
    button.disabled = true;
    try {
      const mode = document.querySelector("#mode").value;
      const result = await post("/api/runs", {
        case_id: button.dataset.start,
        mode,
        browser: true,
      });
      location.href = "/runs/" + result.id;
    } catch (error) {
      document.querySelector("#error").textContent = error.message;
      button.disabled = false;
    }
  }),
);
document.querySelectorAll("[data-review]").forEach((button) =>
  button.addEventListener("click", async () => {
    try {
      await post("/api/runs/" + button.dataset.run + "/review", {
        version: button.dataset.version,
        action: button.dataset.review,
      });
      location.reload();
    } catch (error) {
      document.querySelector("#error").textContent = error.message;
    }
  }),
);
document.querySelectorAll("[data-execute]").forEach((button) =>
  button.addEventListener("click", async () => {
    button.disabled = true;
    try {
      await post("/api/runs/" + button.dataset.execute + "/execute", {
        version: button.dataset.version,
      });
      location.reload();
    } catch (error) {
      document.querySelector("#error").textContent = error.message;
      button.disabled = false;
    }
  }),
);
const run = document.querySelector("[data-run-id]");
if (run && ["queued", "running"].includes(run.dataset.status)) {
  setInterval(async () => {
    try {
      const value = await (
        await fetch("/api/runs/" + run.dataset.runId)
      ).json();
      if (
        value.status !== run.dataset.status ||
        value.events !== Number(run.dataset.events)
      )
        location.reload();
    } catch (error) {}
  }, 2000);
}
