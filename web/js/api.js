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
let recordedRun = null;
let recordedRunPromise = null;

export function setServerStateListener(listener) {
  serverStateListener = listener;
}

function notifyServerState(state) {
  if (serverStateListener) serverStateListener(state);
}

async function requestRecordedRun() {
  const response = await fetch(new URL("../recorded-run.json", import.meta.url));
  if (!response.ok) throw new Error(t("recordedRunUnavailable", {
    detail: `${response.status}${response.statusText ? ` ${response.statusText}` : ""}`,
  }));
  const data = await response.json();
  if (!validateRecordedRun(data)) throw new Error(t("recordedRunInvalid"));
  return data;
}

export function validateRecordedRun(data) {
  const events = data && data.events;
  if (!Array.isArray(events) || events.length < 2) return false;
  const done = events[events.length - 1];
  if (!done || typeof done !== "object" || Array.isArray(done)
      || done.type !== "done" || done.status !== "ok"
      || typeof done.report !== "string" || !done.report.trim()) return false;

  const steps = events.slice(0, -1);
  if (steps.some((event) => !event || event.type !== "step"
      || !Number.isInteger(event.step)
      || typeof event.tool !== "string" || !event.tool
      || !event.args || typeof event.args !== "object" || Array.isArray(event.args)
      || !Object.prototype.hasOwnProperty.call(event, "result")
      || typeof event.decision !== "string")) return false;
  if (done.report.toLowerCase().includes("vérifi")) return false;
  const build = steps[steps.length - 1];
  if (!build || build.tool !== "build_report" || build.result !== done.report) return false;

  const verification = [...steps].reverse().find((event) => event.tool === "verify_report");
  const verificationArgs = verification?.args;
  const buildArgs = build.args;
  return Boolean(
    verification
      && Array.isArray(verification.result)
      && verification.result.length === 0
      && verification.decision === "continue"
      && build.decision === "continue"
      && verificationArgs
      && buildArgs
      && verificationArgs.report
      && verificationArgs.context
      && jsonValuesEqual(verificationArgs.report, buildArgs.report)
      && jsonValuesEqual(verificationArgs.context, buildArgs.context)
  );
}

function jsonValuesEqual(left, right) {
  if (left === right) return true;
  if (!left || !right || typeof left !== "object" || typeof right !== "object") return false;
  if (Array.isArray(left) || Array.isArray(right)) {
    return Array.isArray(left) && Array.isArray(right)
      && left.length === right.length
      && left.every((value, index) => jsonValuesEqual(value, right[index]));
  }
  const leftKeys = Object.keys(left).sort();
  const rightKeys = Object.keys(right).sort();
  return leftKeys.length === rightKeys.length
    && leftKeys.every((key, index) => key === rightKeys[index]
      && jsonValuesEqual(left[key], right[key]));
}

// A proxy or static host answers these when the backend function is missing,
// misrouted or timing out; every other 4xx is a request error to show as is.
const HOSTING_FAILURE_STATUSES = new Set([404, 405, 408]);

export function shouldUseRecordedRun(error) {
  if (Number.isInteger(error?.status) && error.status >= 400 && error.status <= 499) {
    return HOSTING_FAILURE_STATUSES.has(error.status);
  }
  return Boolean(
    error && (
      error.networkFailure === true
      || error.infrastructureFailure === true
      || error.interrupted === true
      || error.name === "AbortError"
      || (Number.isInteger(error.status) && error.status >= 500 && error.status <= 599)
    )
  );
}

export function recordedFailureReason(error) {
  if (error?.interrupted || error?.name === "AbortError") {
    return t(error.messageKey || "interrupted");
  }
  if (error?.networkFailure) return t("serverUnreachable");
  if (Number.isInteger(error?.status) && error.status >= 500) {
    return t("serverFailure", { status: error.status });
  }
  if (error?.infrastructureFailure) return error.message || t("unknownError");
  return describeClientError(error);
}

export function preloadRecordedRun() {
  if (!recordedRunPromise) {
    recordedRunPromise = requestRecordedRun().then((data) => {
      recordedRun = data;
      return data;
    }).catch(() => {
      recordedRunPromise = null;
      return null;
    });
  }
  return recordedRunPromise;
}

export async function fetchRecordedRun() {
  if (recordedRun) return recordedRun;
  if (recordedRunPromise) {
    const preloaded = await recordedRunPromise;
    if (preloaded) return preloaded;
  }
  const data = await requestRecordedRun();
  recordedRun = data;
  recordedRunPromise = Promise.resolve(data);
  return data;
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
  let text;
  try {
    text = await response.text();
  } catch (error) {
    throw markNetworkFailure(error);
  }
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
  if (err?.networkFailure) return t("serverUnreachable");
  if (err && typeof err.message === "string" && err.message.trim()) return err.message;
  return t("unknownError");
}

function markNetworkFailure(error) {
  const wrapped = new Error(
    error && typeof error.message === "string" && error.message
      ? error.message
      : t("serverUnreachable")
  );
  wrapped.networkFailure = true;
  return wrapped;
}

async function responseError(response) {
  let detail;
  try {
    detail = await readErrorDetail(response);
  } catch (error) {
    error.status = response.status;
    throw error;
  }
  const error = new Error(detail);
  error.status = response.status;
  return error;
}

export async function streamEvents(response, onEvent) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let terminalSeen = false;
  let parseErrors = 0;
  const dispatch = async (line) => {
    if (!line.startsWith("data:")) return;
    let event;
    try {
      event = JSON.parse(line.slice(5).trim());
    } catch {
      parseErrors += 1;
      return;
    }
    if (!event || typeof event !== "object" || Array.isArray(event)) {
      parseErrors += 1;
      return;
    }
    if (event.type === "done" || event.type === "needs_input" || event.type === "error") {
      terminalSeen = true;
    }
    try {
      await onEvent(event);
    } catch (error) {
      reader.cancel().catch(() => {});
      throw error;
    }
  };
  for (;;) {
    let chunk;
    try {
      chunk = await reader.read();
    } catch (error) {
      throw markNetworkFailure(error);
    }
    const { done, value } = chunk;
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let cut;
    while ((cut = buffer.indexOf("\n\n")) >= 0) {
      const block = buffer.slice(0, cut);
      buffer = buffer.slice(cut + 2);
      for (const line of block.split("\n")) await dispatch(line);
    }
  }
  const tail = buffer.trim();
  if (tail) await dispatch(tail);
  return { terminalSeen, parseErrors };
}

async function streamResponse(response, onEvent, interruptedMessageKey = "interrupted") {
  const result = await streamEvents(response, (event) => {
    onEvent(event);
    if (event.type === "error") {
      const error = new Error(event.error || "run failed");
      error.category = event.category || "application";
      error.infrastructureFailure = error.category === "infrastructure";
      throw error;
    }
  });
  if (!result.terminalSeen) {
    const error = new Error(t(interruptedMessageKey));
    error.interrupted = true;
    error.messageKey = interruptedMessageKey;
    throw error;
  }
  return result;
}

export async function streamRun(body, onEvent) {
  await ensureApiBase();
  let response;
  try {
    response = await fetch(`${apiBase}/run`, { method: "POST", body });
  } catch (error) {
    throw markNetworkFailure(error);
  }
  if (!response.ok) throw await responseError(response);
  return streamResponse(response, onEvent);
}

export async function streamAnswer(runId, answer, onEvent) {
  await ensureApiBase();
  let response;
  try {
    response = await fetch(`${apiBase}/answer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ run_id: runId, answer }),
    });
  } catch (error) {
    throw markNetworkFailure(error);
  }
  if (!response.ok) throw await responseError(response);
  return streamResponse(response, onEvent, "answerInterrupted");
}

export async function fetchSampleFile(name) {
  await ensureApiBase();
  let response;
  try {
    response = await fetch(`${apiBase}/samples/${name}`);
  } catch (error) {
    throw markNetworkFailure(error);
  }
  if (!response.ok) {
    const error = await responseError(response);
    error.message = t("sampleUnreadable", { name, detail: error.message });
    throw error;
  }
  let blob;
  try {
    blob = await response.blob();
  } catch (error) {
    throw markNetworkFailure(error);
  }
  return new File([blob], name, { type: blob.type || "application/octet-stream" });
}
