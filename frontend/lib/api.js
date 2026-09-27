// Thin fetch client for the Nexus API. The session cookie is HttpOnly (the browser sends it; JavaScript never sees it).
// The CSRF token lives only in memory and is sent as X-CSRF-Token on every mutation.
export class ApiError extends Error {
  /** @param {number} status @param {string} code @param {string} message */
  constructor(status, code, message) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

let csrfToken = null;

/** Who am I, plus a CSRF token (session token when signed in, pre-session token otherwise). */
export async function fetchSession() {
  const res = await fetch("/api/v1/session", { credentials: "same-origin", cache: "no-store" });
  const data = await res.json();
  csrfToken = data.csrf;
  return data;
}

async function parse(res) {
  if (res.status === 204) return null;
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const err = new ApiError(res.status, data?.error?.code ?? "unknown", data?.error?.message ?? "Something went wrong. Please try again.");
    err.retry_after = data?.error?.retry_after; // seconds to wait, when the server is limiting requests
    throw err;
  }
  return data;
}

/**
 * @param {string} path  e.g. "/subjects"
 * @param {{method?: string, json?: unknown, form?: FormData, signal?: AbortSignal}} [opts]
 */
export async function api(path, { method = "GET", json, form, signal } = {}) {
  const headers = {};
  if (method !== "GET") {
    if (!csrfToken) await fetchSession();
    headers["X-CSRF-Token"] = csrfToken;
  }
  let body;
  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(json);
  } else if (form) body = form;
  const res = await fetch(`/api/v1${path}`, { method, headers, body, signal, credentials: "same-origin", cache: "no-store" });
  const data = await parse(res);
  if (data && typeof data.csrf === "string") csrfToken = data.csrf; // login/register hand back the new session token
  return data;
}

/** Upload one file with progress (fetch cannot report upload progress). Resolves with the parsed JSON body. */
export function uploadFile(path, file, onProgress, fields = {}) {
  return new Promise(async (resolve, reject) => {
    if (!csrfToken) await fetchSession();
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `/api/v1${path}`);
    xhr.setRequestHeader("X-CSRF-Token", csrfToken);
    xhr.upload.onprogress = (e) => e.lengthComputable && onProgress?.(Math.round((100 * e.loaded) / e.total));
    xhr.onload = () => {
      let data = null;
      try {
        data = JSON.parse(xhr.responseText);
      } catch {}
      if (xhr.status >= 200 && xhr.status < 300) resolve(data);
      else if (xhr.status === 413) reject(new ApiError(413, "too_large", "That file is too large."));
      else reject(new ApiError(xhr.status, data?.error?.code ?? "unknown", data?.error?.message ?? "The upload failed."));
    };
    xhr.onerror = () => reject(new ApiError(0, "network", "Could not reach the server."));
    const form = new FormData();
    form.append("file", file);
    for (const [k, v] of Object.entries(fields)) form.append(k, v);
    xhr.send(form);
  });
}

/** Empties what the offline service worker saved of the signed-in person's data. Called on every log in and log out. */
export function clearOfflineData() {
  try {
    navigator.serviceWorker?.controller?.postMessage("clear-data");
    caches?.keys().then((ks) => ks.filter((k) => k.endsWith("-data")).forEach((k) => caches.delete(k)));
  } catch {}
}
