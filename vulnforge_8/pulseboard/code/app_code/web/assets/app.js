const form = document.getElementById("health-form");
const region = document.getElementById("region");
const idFilter = document.getElementById("id-filter");
const result = document.getElementById("result");
const regionPattern = /^[a-z0-9-]+$/;

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const regionValue = region.value.trim().toLowerCase();
  const idValue = idFilter.value.trim();

  if (!regionPattern.test(regionValue)) {
    result.textContent = "Use letters, numbers, or hyphens for the region filter.";
    return;
  }

  if (idValue && !/^\d+$/.test(idValue)) {
    result.textContent = "ID filter must contain digits only.";
    return;
  }

  const button = form.querySelector("button");
  button.disabled = true;
  result.textContent = "Refreshing connector health…";

  try {
    const response = await fetch("/api/integrations/check", {
      method: "POST",
      credentials: "same-origin",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        filter: {
          field: "region",
          operator: "contains",
          value: regionValue
        },
        id_filter: idValue
      })
    });

    if (!response.ok) {
      throw new Error("request failed");
    }

    result.textContent = "Connector health refresh completed.";
  } catch {
    result.textContent = "The health refresh could not be completed.";
  } finally {
    button.disabled = false;
  }
});
