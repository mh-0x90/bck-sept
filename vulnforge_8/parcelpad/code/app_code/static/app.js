(() => {
  const form = document.querySelector("#finalize-form");
  if (!form) return;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector("button[type='submit']");
    const stageNumber = document.querySelector("#stage-number");
    const progress = document.querySelector("#progress");
    const title = document.querySelector("#stage-title");
    const body = document.querySelector("#stage-body");
    const actions = document.querySelector("#actions");

    button.disabled = true;
    stageNumber.textContent = "Stage 10 of 10";
    progress.value = 10;
    title.textContent = "Final processing";
    body.innerHTML = '<div class="processing" role="status"><span class="spinner" aria-hidden="true"></span><p>Final processing is in progress.</p></div>';
    actions.querySelectorAll("form").forEach((node) => { node.hidden = true; });

    try {
      const response = await fetch(form.action, {
        method: "POST",
        body: new FormData(form),
        credentials: "same-origin",
        headers: { "Accept": "application/json" },
      });
      const result = await response.json();
      body.innerHTML = "";
      const message = document.createElement("p");
      message.className = result.ok ? "notice" : "notice error";
      message.textContent = result.message || "Processing finished.";
      body.appendChild(message);
      const home = document.createElement("a");
      home.className = "button";
      home.href = "/";
      home.textContent = "Back to operations";
      actions.appendChild(home);
    } catch (error) {
      body.innerHTML = '<p class="notice error">The request could not be completed.</p>';
      button.disabled = false;
      form.hidden = false;
    }
  });
})();
