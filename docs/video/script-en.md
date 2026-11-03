# Voice-over script — English (primary cut for the jury)

Total on screen: 2:58 at most (hard limit 3:00). Voice-over only: no face, no music with lyrics.
Pace: about 2.2 words per second, with silences kept for the interface. Each block lists its window, its shot ids (see `production-plan.md`) and its word budget; the word count is checked in `production-plan.md`.

Read plain and calm, like explaining to a colleague. Numbers are said in full. "Baccalauréat" is pronounced the French way.

---

## V1 · 0:00–0:20 · The strong moment (shots S01, S02)

A student says she averaged fourteen out of twenty. Her grade sheet says eleven point two. Most tools would pick one and carry on. This agent stops, and asks her. This is PathProof: every study path comes with its proof.

## V2 · 0:20–0:45 · The problem, one sourced figure (shots S03, S04)

In June 2026, seventy-seven thousand candidates sat the Baccalauréat in Benin. Choosing a program can come down to rumor. Yet the official guide ranks you program by program, on three subjects, with your series' coefficients. Not on your overall average. PathProof computes that, and shows its proof.

## V3a · 0:45–1:05 · A full case, the inputs (shots S05, S06)

Here is a full run, on a fictional serie D student. A grade-sheet photo and a voice note go in. The agent chooses its own tools, step by step, and each step shows which Meta model decided and which one ran it.

## V3b · 1:05–1:30 · A full case, the trace (shots S07, S08)

Muse Voice Transcribe hears the note. Muse Spark reads the sheet. The Contributor picks the next tool, and asks one question before going on. Then plain code, not the model, filters the programs and computes the averages. Wonder drafts the report.

## V3c · 1:30–2:00 · A full case, the proofs (shots S09, S10, S11)

Medicine ranks at thirteen point one five, above her Baccalauréat average of eleven point two. The formula keeps three subjects, and biology, her best, counts five times. Every sentence opens its proof: the grade read on the photo, her own words, the guide row and its page, the calculation. A code verifier blocks any claim without one.

## V4 · 2:00–2:30 · A hard case (shots S12, S13)

Now a hard case. Same student, blurry photo: the Mathematics grade cannot be read. The agent does not guess, and does not deduce it from the total. It asks for a sharper photo. We also tested SAM 3.1 to zoom on one cell. It found the table, never the cell, so we dropped it.

## V5 · 2:30–2:50 · The evaluations and a dropped row (shots S14, S15)

We ran eleven fictional cases through the real agent: all eleven comply, one pass each. The verifier found no claim without proof. A student who wants pharmacy? That row of the guide did not pass quality control, so it comes back as excluded, never recommended.

## V6 · 2:50–2:58 · What is new, limits, team (shot S16)

Built solo during this hackathon. Fictional data, series C and D only. Try it at pathproof-six.vercel.app.

---

## English subtitles

The English subtitles are this text, cut into cues of at most two lines of 42 characters (horizontal) or 28 characters (vertical), timed on the recorded voice. For the French voice-over cut, the same English cues are used and timed on the French audio.
