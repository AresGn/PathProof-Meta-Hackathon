// Demo API client: base resolution, SSE streaming, sample files, errors.
// No display code here; views live in steps.js, proofs.js and report.js.
import { t } from "./i18n.js";

// The API normally shares the page origin (uvicorn serves both). Opened via
// a static preview (Live Server, file), the page falls back to the local
// uvicorn port instead of calling a server that has no API at all.
const LOCAL_API_BASE = "http://127.0.0.1:8000";

let apiBase = "";
let apiBasePromise = null;
let serverStateListener = null;

export function setServerStateListener(listener) {
  serverStateListener = listener;
}

function notifyServerState(state) {
  if (serverStateListener) serverStateListener(state);
}

async function probeApiBase(base) {
  const response = await fetch(`${base}/health`);
  const data = await response.json();
  if (!response.ok || data.service !== "pathproof-demo") throw new Error("unexpected");
  return base;
}

export function ensureApiBase() {
  if (!apiBasePromise) {
    apiBasePromise = (async () => {
      try {
        apiBase = await probeApiBase("");
        notifyServerState("ready");
        return apiBase;
      } catch {
        const host = window.location.hostname;
        const isLocalPage = ["127.0.0.1", "localhost", ""].includes(host);
        if (isLocalPage && window.location.origin !== LOCAL_API_BASE) {
          try {
            apiBase = await probeApiBase(LOCAL_API_BASE);
            notifyServerState("ready-local");
            return apiBase;
          } catch {
            // Fall through to the unreachable state below.
          }
        }
        notifyServerState("down");
        return "";
      }
    })();
  }
  const currentPromise = apiBasePromise;
  return currentPromise.then((result) => {
    if (!result && apiBasePromise === currentPromise) apiBasePromise = null;
    return result;
  });
}

export async function readErrorDetail(response) {
  const text = await response.text();
  let parsed = null;
  try {
    parsed = JSON.parse(text);
  } catch {
    parsed = null;
  }
  const detail = parsed && typeof parsed === "object" ? parsed.detail : null;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail) && detail.length) {
    return detail.map((item) => (item && item.msg) || JSON.stringify(item)).join(" ; ");
  }
  if (text && text.trim()) return text.trim().slice(0, 500);
  return t("serverNoDetail", {
    status: `${response.status}${response.statusText ? ` ${response.statusText}` : ""}`,
  });
}

// Never surface an empty error: name the cause or say the server is down.
export function describeClientError(err) {
  if (err && err.name === "TypeError") return t("serverUnreachable");
  if (err && typeof err.message === "string" && err.message.trim()) return err.message;
  return t("unknownError");
}

export async function streamEvents(response, onEvent) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let terminalSeen = false;
  let parseErrors = 0;
  const dispatch = (line) => {
    if (!line.startsWith("data:")) return;
    try {
      const event = JSON.parse(line.slice(5).trim());
      if (event.type === "done" || event.type === "needs_input" || event.type === "error") {
        terminalSeen = true;
      }
      onEvent(event);
    } catch {
      parseErrors += 1;
    }
  };
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let cut;
    while ((cut = buffer.indexOf("\n\n")) >= 0) {
      const block = buffer.slice(0, cut);
      buffer = buffer.slice(cut + 2);
      for (const line of block.split("\n")) dispatch(line);
    }
  }
  const tail = buffer.trim();
  if (tail) dispatch(tail);
  return { terminalSeen, parseErrors };
}

export async function streamRun(body, onEvent) {
  await ensureApiBase();
  const response = await fetch(`${apiBase}/run`, { method: "POST", body });
  if (!response.ok) throw new Error(await readErrorDetail(response));
  const result = await streamEvents(response, onEvent);
  if (!result.terminalSeen) throw new Error(t("interrupted"));
}

export async function streamAnswer(runId, answer, onEvent) {
  await ensureApiBase();
  const response = await fetch(`${apiBase}/answer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ run_id: runId, answer }),
  });
  if (!response.ok) {
    const error = new Error(await readErrorDetail(response));
    error.status = response.status;
    throw error;
  }
  return streamEvents(response, onEvent);
}

export async function fetchSampleFile(name) {
  await ensureApiBase();
  const response = await fetch(`${apiBase}/samples/${name}`);
  if (!response.ok) {
    throw new Error(t("sampleUnreadable", { name, detail: await readErrorDetail(response) }));
  }
  const blob = await response.blob();
  return new File([blob], name, { type: blob.type || "application/octet-stream" });
}
