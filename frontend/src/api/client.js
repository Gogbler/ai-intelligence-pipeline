const API_BASE = "/api";

export async function fetchStats() {
  const res = await fetch(`${API_BASE}/stats`);
  if (!res.ok) throw new Error("Failed to fetch stats");
  return res.json();
}

export async function fetchSources() {
  const res = await fetch(`${API_BASE}/sources`);
  if (!res.ok) throw new Error("Failed to fetch sources");
  return res.json();
}

export async function fetchLLMMetrics() {
  const res = await fetch(`${API_BASE}/llm/metrics`);
  if (!res.ok) throw new Error("Failed to fetch LLM metrics");
  return res.json();
}

export async function triggerLLMRun() {
  const res = await fetch(`${API_BASE}/llm/run`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to trigger LLM resilience benchmark");
  return res.json();
}

export async function fetchEntityMappings(limit = 25) {
  const res = await fetch(`${API_BASE}/entity-mappings?limit=${limit}`);
  if (!res.ok) throw new Error("Failed to fetch entity mappings");
  return res.json();
}

export async function fetchRecentActivity() {
  const res = await fetch(`${API_BASE}/recent-activity`);
  if (!res.ok) throw new Error("Failed to fetch recent activity");
  return res.json();
}

export async function triggerPipelineRun() {
  const res = await fetch(`${API_BASE}/pipeline/run`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to trigger pipeline");
  return res.json();
}

export async function fetchPipelineStatus() {
  const res = await fetch(`${API_BASE}/pipeline/status`);
  if (!res.ok) throw new Error("Failed to fetch pipeline status");
  return res.json();
}

export async function fetchExports() {
  const res = await fetch(`${API_BASE}/exports`);
  if (!res.ok) throw new Error("Failed to fetch exports metadata");
  return res.json();
}
