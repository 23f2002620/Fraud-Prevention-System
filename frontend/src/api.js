const API_BASE = "http://localhost:8000";
let token = "";

export async function login(username, password) {
  const form = new URLSearchParams();
  form.append("username", username);
  form.append("password", password);

  const res = await fetch(`${API_BASE}/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form.toString()
  });
  if (!res.ok) throw new Error("Login failed");
  const data = await res.json();
  token = data.access_token;
  return data;
}

function authHeaders() {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function getCases(status = "") {
  const url = status ? `${API_BASE}/cases?status=${encodeURIComponent(status)}` : `${API_BASE}/cases`;
  const res = await fetch(url, { headers: { ...authHeaders() } });
  if (!res.ok) throw new Error(`Failed to load cases (${res.status})`);
  return await res.json();
}

export async function updateCaseStatus(caseId, status) {
  const url = `${API_BASE}/cases/${caseId}?status=${encodeURIComponent(status)}`;
  const res = await fetch(url, { method: "PATCH", headers: { ...authHeaders() } });
  if (!res.ok) throw new Error(`Failed to update case (${res.status})`);
  return await res.json();
}

export async function createCase(payload) {
  const res = await fetch(`${API_BASE}/cases`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error(`Failed to create case (${res.status})`);
  return await res.json();
}

export async function scoreTxn(txn) {
  const res = await fetch(`${API_BASE}/score`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(txn)
  });
  if (!res.ok) throw new Error(`Failed to score (${res.status})`);
  return await res.json();
}
