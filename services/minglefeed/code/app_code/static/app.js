const pending = [...document.querySelectorAll('.preview')].some((node) =>
  ['queued', 'processing'].includes(node.dataset.status)
);

if (pending) {
  const poll = async () => {
    try {
      const response = await fetch('/api/previews', {cache: 'no-store'});
      if (!response.ok) return;
      const states = await response.json();
      let changed = false;
      document.querySelectorAll('.preview').forEach((node) => {
        const next = states[node.dataset.postId]?.status;
        if (next && next !== node.dataset.status) changed = true;
      });
      if (changed) window.location.reload();
      else window.setTimeout(poll, 1500);
    } catch {
      window.setTimeout(poll, 2500);
    }
  };
  window.setTimeout(poll, 1000);
}
