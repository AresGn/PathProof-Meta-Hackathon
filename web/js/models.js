// Which Meta model decided each step and which one ran each tool.
// The deciding model comes from the journal (`step.model`, stamped by
// src/agent/loop.py with the model that really answered); only the models
// that tools call internally are listed here, mirroring src/clients/
// (tests/test_web_ui.py fails if an identifier drifts).
export const MODELS = {
  "muse-spark-1.3-contributor": { id: "muse-spark-1.3-contributor", name: "Muse Spark 1.3 Contributor", tone: "spark" },
  "muse-wonder-1.0": { id: "muse-wonder-1.0", name: "Muse Wonder 1.0", tone: "wonder", effort: "high" },
  "muse-spark-1.3": { id: "muse-spark-1.3", name: "Muse Spark 1.3", tone: "vision" },
  "muse-voice-transcribe-1.0": { id: "muse-voice-transcribe-1.0", name: "Muse Voice Transcribe 1.0", tone: "voice" },
};
export const MODEL_ORDER = [
  "muse-spark-1.3-contributor", "muse-wonder-1.0", "muse-spark-1.3", "muse-voice-transcribe-1.0",
];

// Tools that call a model themselves; every other tool is deterministic code.
export const TOOL_MODELS = {
  transcribe_voice: "muse-voice-transcribe-1.0",
  read_grade_sheet: "muse-spark-1.3",  // vision: src/clients/vision.py
  extract_profile: "muse-spark-1.3",  // src/clients/profile.py
};

// A model the page does not know is still shown by its identifier.
export function modelInfo(id) {
  return MODELS[id] || { id, name: id, tone: "spark" };
}

export function deciderOf(step) {
  return step.model ? modelInfo(step.model) : null;
}

export function runnerOf(tool) {
  const id = TOOL_MODELS[tool];
  return id ? MODELS[id] : null;
}

// Calls per model so far: one decision per distinct (step, model) turn, plus
// the tools that call a model inside their own execution; the rest is code.
export function countModelCalls(steps) {
  const counts = { code: 0 };
  for (const id of MODEL_ORDER) counts[id] = 0;
  const turns = new Set();
  for (const step of steps) {
    if (step.model) {
      const turn = `${step.step}:${step.model}`;
      if (!turns.has(turn)) {
        turns.add(turn);
        counts[step.model] = (counts[step.model] || 0) + 1;
      }
    }
    const runner = TOOL_MODELS[step.tool];
    if (runner) counts[runner] += 1;
    else counts.code += 1;
  }
  return counts;
}
