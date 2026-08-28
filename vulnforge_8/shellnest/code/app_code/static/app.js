(() => {
  const form = document.querySelector("#command-form");
  const input = document.querySelector("#command");
  const terminal = document.querySelector("#terminal");
  const status = document.querySelector("#status");

  function addLine(text, kind = "") {
    const line = document.createElement("div");
    line.className = `line ${kind}`.trim();
    line.textContent = text;
    terminal.appendChild(line);
    terminal.scrollTop = terminal.scrollHeight;
  }

  async function checkStatus() {
    try {
      const response = await fetch("/api/status", {
        headers: { Accept: "application/json" }
      });
      const data = await response.json();
      const connected = response.ok && data.ok;
      status.className = `status ${connected ? "online" : "offline"}`;
      status.lastElementChild.textContent = connected ? "connected" : "offline";
    } catch {
      status.className = "status offline";
      status.lastElementChild.textContent = "offline";
    }
  }

  async function run(command) {
    addLine(`shellnest › ${command}`, "command");

    try {
      const response = await fetch("/api/run", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json"
        },
        body: JSON.stringify({ command })
      });

      const data = await response.json();

      if (!response.ok || !data.ok) {
        addLine(data.error || "request failed", "error");
        return;
      }

      if (data.stdout) {
        addLine(data.stdout.replace(/\n$/, ""));
      }

      if (data.stderr) {
        addLine(data.stderr.replace(/\n$/, ""), "error");
      }

      if (!data.stdout && !data.stderr) {
        addLine(`exit ${data.code}`, "muted");
      }
    } catch {
      addLine("server unavailable", "error");
    }
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();

    const command = input.value.trim();
    if (!command) return;

    input.value = "";
    run(command);
  });

  checkStatus();
  input.focus();
})();
