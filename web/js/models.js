// Which Meta model answers each tool of the agent loop.
// Mirrors src/clients/muse_spark.py (MUSE_SPARK_MODEL) and src/clients/voice.py
// (VOICE_MODEL); tests/test_web_ui.py fails if the identifiers drift apart.
export const MODELS = {
  spark: { id: "muse-spark-1.3", name: "Muse Spark 1.3" },
  voice: { id: "muse-voice-transcribe-1.0", name: "Muse Voice Transcribe 1.0" },
};

// Every loop step is one Muse Spark turn that picks the tool (src/agent/loop.py).
export const ORCHESTRATOR = "spark";

// Tools that call a model themselves; every other tool is deterministic code.
export const TOOL_MODELS = {
  transcribe_voice: "voice",
  read_grade_sheet: "spark",  // vision: src/clients/vision.py
  extract_profile: "spark",  // src/clients/profile.py
};

export function modelOfTool(tool) {
  const key = TOOL_MODELS[tool];
  return key ? MODELS[key] : null;
}

// Model calls so far: one Muse Spark turn per distinct step number, plus the
// tools that call a model inside their own execution.
export function countModelCalls(steps) {
  const counts = { spark: 0, voice: 0, code: 0 };
  counts[ORCHESTRATOR] = new Set(steps.map((step) => step.step)).size;
  for (const step of steps) {
    const key = TOOL_MODELS[step.tool];
    if (key) counts[key] += 1;
    else counts.code += 1;
  }
  return counts;
}
