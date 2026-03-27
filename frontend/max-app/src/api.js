const API = {
  auth: "/max/auth/validate/",
  reference: "/max/api/reference/",
  submitSingle: "/max/api/tkp/single/submit/",
  submitComplex: "/max/api/tkp/complex/submit/",
  parseReq: "/max/api/requisites/parse/",
  saveReq: "/max/api/requisites/save/",
  counterparties: "/max/api/counterparties/",
  counterpartyDetail: "/max/api/counterparties/",
  tkps: "/max/api/tkps/",
  submitContract: "/max/api/contract/submit/",
};

function headers(token, isJson = true) {
  const h = {};
  if (isJson) h["Content-Type"] = "application/json";
  if (token) h["X-Max-App-Token"] = token;
  return h;
}

export async function initAuth() {
  const params = new URLSearchParams(window.location.search || "");
  const initData =
    window.WebApp?.initData ||
    window.MAX?.WebApp?.initData ||
    window.max?.WebApp?.initData ||
    window.MAX?.initData ||
    window.max?.initData ||
    params.get("initData") ||
    params.get("maxWebAppData") ||
    params.get("webAppData") ||
    "";
  const res = await fetch(API.auth, {
    method: "POST",
    headers: headers(null, true),
    body: JSON.stringify({ initData }),
  });
  return res.json();
}

export async function getReference(token) {
  const res = await fetch(API.reference, { headers: headers(token, false) });
  return res.json();
}

export async function submitSingle(token, payload) {
  const res = await fetch(API.submitSingle, {
    method: "POST",
    headers: headers(token, true),
    body: JSON.stringify(payload),
  });
  return res.json();
}

export async function submitComplex(token, payload) {
  const res = await fetch(API.submitComplex, {
    method: "POST",
    headers: headers(token, true),
    body: JSON.stringify(payload),
  });
  return res.json();
}

export async function saveRequisites(token, payload) {
  const res = await fetch(API.saveReq, {
    method: "POST",
    headers: headers(token, true),
    body: JSON.stringify(payload),
  });
  return res.json();
}

export async function parseRequisites(token, file) {
  const formData = new FormData();
  formData.append("source_file", file);
  const res = await fetch(API.parseReq, {
    method: "POST",
    headers: headers(token, false),
    body: formData,
  });
  return res.json();
}

export async function listCounterparties(token, q = "") {
  const res = await fetch(`${API.counterparties}?q=${encodeURIComponent(q)}`, {
    headers: headers(token, false),
  });
  return res.json();
}

export async function getCounterparty(token, id) {
  const res = await fetch(`${API.counterpartyDetail}${id}/`, {
    headers: headers(token, false),
  });
  return res.json();
}

export async function listTkps(token, q = "") {
  const res = await fetch(`${API.tkps}?q=${encodeURIComponent(q)}`, {
    headers: headers(token, false),
  });
  return res.json();
}

export async function submitContract(token, payload) {
  const res = await fetch(API.submitContract, {
    method: "POST",
    headers: headers(token, true),
    body: JSON.stringify(payload),
  });
  return res.json();
}
