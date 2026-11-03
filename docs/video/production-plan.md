# Video production plan (story E7.2, issue #39)

**Status (3 Nov):** the four exports were made and the video is published on YouTube (link in the README). This plan is kept as the production record.

A **face-less** video: a filmed browser screen, a voice-over, English subtitles. 3:00 at most, in two formats (horizontal for YouTube, vertical for X) and two voice languages (English, French).
Voice-over texts: [`script-en.md`](script-en.md) and [`script-fr.md`](script-fr.md) (the French voice-over, kept in French on purpose). Starting sequence: `docs/prd.md` §13 and `docs/demo-script.md`.

## 1. Deliverables

| Priority | File | Format | Voice | English subtitles |
|---|---|---|---|---|
| **P1** | `pathproof_youtube_en.mp4` | 1920×1080, 16:9 | English | `.srt` track (YouTube) + `pathproof_en.srt` |
| **P2** | `pathproof_x_en_vertical.mp4` | 1080×1920, 9:16 | English | burned in |
| P3 | `pathproof_youtube_fr.mp4` | 1920×1080 | French | `.srt` track (English cues timed on the French voice) |
| P3 | `pathproof_x_fr_vertical.mp4` | 1080×1920 | French | burned in |

The jury is mostly English-speaking: **P1 is what gets submitted**. P2 is for the X post (E7.3). P3 is done if time remains; the submission must not depend on it.
All versions last **2:58 at most** (limit 3:00), with the same block split and the same shot numbers.

> **To check before publishing on X:** a non-Premium X account caps the duration of a video (probably 2:20, not verified). If the account is affected, a shortened version will be needed, hence a second set of texts: to decide before cutting P2.

## 2. Who does what

| Who | Task |
|---|---|
| **You** | Film the screen (§4), record the voice (§5), choose the title, the thumbnail and the X account, publish. |
| **Code agent (montage)** | Assemble, cut the waits, zoom, burn in cards and subtitles, set the sound, export and check durations (§6). It works with `ffmpeg` on the command line, on files you drop into `video/raw/`. |
| **Neither** | Invent a shot. Everything on screen comes from a real run or from a clearly marked card (§7). |

The media do not go into the repository (heavy, and raw footage may contain noise): `video/` stays out of git. The repository only keeps these three documents, and the final `.srt` if you want to version it.

## 3. Split: 16 shots, 6 voice blocks

Windows set by PRD §13 and by issue #39. Controlled pace: English stays under 2.3 words/s, French under 2.6 words/s, which leaves silences for the interface.

| Block | Window | Shots | EN words (words/s) | FR words (words/s) |
|---|---|---|---|---|
| V1 strong moment | 0:00–0:20 | S01, S02 | 40 (2.0) | 42 (2.1) |
| V2 problem and figure | 0:20–0:45 | S03, S04 | 47 (1.9) | 50 (2.0) |
| V3a full case: inputs | 0:45–1:05 | S05, S06 | 42 (2.1) | 41 (2.1) |
| V3b full case: trace | 1:05–1:30 | S07, S08 | 41 (1.6) | 41 (1.6) |
| V3c full case: proofs | 1:30–2:00 | S09, S10, S11 | 57 (1.9) | 64 (2.1) |
| V4 hard case | 2:00–2:30 | S12, S13 | 54 (1.8) | 55 (1.8) |
| V5 evaluations and dropped row | 2:30–2:50 | S14, S15 | 45 (2.3) | 51 (2.6) |
| V6 what is new, limits, team | 2:50–2:58 | S16 | 16 (2.0) | 17 (2.1) |
| **Total** | **2:58** | | **342** | **361** |

### Shot by shot

"Run" = capture of a real PathProof run. "Card" = an image made at the montage stage, with no run, marked as such.

| Shot | Window | On screen | Source |
|---|---|---|---|
| S01 | 0:00–0:10 | The fictional sheet (`releve_serie_d.jpg`, average **11.20**) and the voice-note transcript "… j'ai eu 14 de moyenne" side by side. Option: the audio excerpt of the note, at −22 dB under the voice | Run (click on **Contradictory voice note**, `transcribe_voice` step) + the input file |
| S02 | 0:10–0:20 | The agent stops: "Vous avez déclaré 14/20, mais votre relevé affiche 11.2/20…" (You declared 14/20, but your sheet shows 11.2/20), status "Agent is waiting for your answer" | Run (same take, 2nd question) |
| S03 | 0:20–0:32 | **Card**: "77,101 candidates for the 2026 BAC", source "Office du Baccalauréat data relayed by Bénin Web TV, 14 June 2026". A single figure in the whole video | Card (`docs/impact.md`) |
| S04 | 0:32–0:45 | In a real report, the "Ranking average" section: formula `M = Σ(mi·ci)/Σci (guide, page 8)` and the three subjects with their coefficients | Run (report of S09) |
| S05 | 0:45–0:55 | `demo.html`, click on **Clear serie D sheet + matching voice note**; caption "fictional, synthetic voice" | Run |
| S06 | 0:55–1:05 | The launch: the agent map lights up tool by tool (sped up ×3, "×3" badge visible) | Run |
| S07 | 1:05–1:17 | Close-up of the trace: badges "Decided by Muse Spark 1.3 Contributor", "Run by Muse Voice Transcribe 1.0", "Run by Muse Spark 1.3" | Run |
| S08 | 1:17–1:30 | The question, the answer "D", then `lookup_filieres` "Run by deterministic code · no model" and the Muse Wonder 1.0 step ("effort high"); wait sped up ×4 | Run |
| S09 | 1:30–1:42 | The banner "Verified report — every claim checked by code", scroll down to Medicine **13.15** | Run |
| S10 | 1:42–1:52 | Click on the proof chips: "Grade · SVT 15/20", "Quote · "peut-être médecin"" (proof dialog with the quote highlighted) | Run |
| S11 | 1:52–2:00 | Click on "Guide · PUB-062 (page 36)" then "Result · 13.15"; end on the "All claims proven" step | Run |
| S12 | 2:00–2:12 | Click on **Blurry sheet**: the blurry sheet, the agent reads it | Run |
| S13 | 2:12–2:30 | The question "the Mathematics grade is unreadable…" and the agent waiting; then a card: "SAM 3.1: table found, cell never found (0/3) → dropped", source `docs/spikes/sam` | Run + card |
| S14 | 2:30–2:42 | In the public repository, the table of `evals/results/summary.md`: **11 of 11 cases compliant** (slow scroll) | GitHub page of the repository |
| S15 | 2:42–2:50 | Pharmacie case: serie D sheet + text `intention_pharmacien.txt`, `lookup_filieres` step, expand "Input / output": the "Pharmacie" row is among the excluded rows (`Statut_qualité` "Réparé - fusion OCR") and does not appear in the recommendations | Run; **fallback**: the file `evals/results/2026-11-03/unverified_trap.json`, captioned as such |
| S16 | 2:50–2:58 | End **card**: PathProof, `pathproof-six.vercel.app`, `github.com/AresGn/PathProof-Meta-Hackathon`, X account `{{X_HANDLE}}`, "Solo · fictional data" | Card |

## 4. Screen capture

### Preparation (once)
1. Server: `.venv/bin/uvicorn src.api.server:app --port 8000`, then open `http://127.0.0.1:8000/demo.html` (the page served by uvicorn, not a static preview).
2. **Record the browser only** (OBS "window" source, not the whole screen): no editor or terminal window in the frame. **`.env` must never appear**, nor the address bar of another tab, nor a personal path.
3. Browser in a private window, no extensions, bookmarks bar hidden, a single tab, notifications off ("do not disturb" mode).
4. Settings: 1920×1080, 30 fps, MKV (remux to MP4 afterwards), visible cursor with a discreet halo.
5. Interface language: **choose EN or FR before launching** (the report and the questions follow the language chosen at start). English version: EN interface. French version: FR interface, separate raw footage.
6. Raw footage of a full run lasts 100 to 165 s (measured, `docs/deploy.md`, `evals/results/summary.md`): shoot without cutting, the montage speeds up the waits.

### Where to film
- **Local server** for the takes: same code as the deployment, no per-IP limit (5 requests/min on Vercel) and without the `ask_student` session 404 known on Vercel (`docs/deploy.md`).
- **Public URL** for **one** take of S05/S06: proof that the deployed demo runs. If the 404 appears, keep the local take.

### Take list

| Take | What | Shots | Indicative cost (loop only, `evals/results/summary.md`) |
|---|---|---|---|
| T1 | **Contradictory voice note**: answer "D" to the 1st question, leave the 2nd (14 vs 11.2) displayed for 10 s | S01, S02 | ≈ $0.32 |
| T2 | **Clear serie D sheet + matching voice note**, answer "D", then go through the report and the proofs | S04–S11 | ≈ $0.38 |
| T3 | **Blurry sheet** | S12, S13 | ≈ $0 |
| T4 | Pharmacie: sheet `releve_serie_d.jpg` + text from `intention_pharmacien.txt` | S15 | ≈ $0.35 |
| T5 | GitHub: `summary.md`, slow scroll | S14 | 0 |

Plan 2 to 3 attempts per take: about $5 per language, far below the credit balance ($66 on 3 Nov, according to the owner).

**Retake if:** the "recorded run" banner appears (this is not a live take; if you keep it, the voice must say so); the 2nd question of T1 is not the 14 vs 11.2 one (behaviour varies from one run to another); the 12-step limit is reached without a report (`docs/deploy.md`); a key, a real name or a personal path is visible.

### Raw file naming
`video/raw/<shot>_<language>_<format>_take<n>.mkv`, for example `S08_en_desktop_take2.mkv`, `S13_fr_vertical_take1.mkv`. One line of `video/raw/NOTES.txt` per kept take: "good", "retake", and why.

### Vertical format (X)
- **Native capture**: narrow window, `chromium --app=http://127.0.0.1:8000/demo.html --window-size=540,960 --force-device-scale-factor=2`, recorded at 1080×1920. The interface is responsive (375 px captures in `docs/`), so the same take can be redone in vertical.
- **Fallback**: crop the horizontal footage around the active panel (zoom at the montage stage). Less sharp, but without redoing the takes.
- Safe zones: text and subtitles between 12 % and 82 % of the height, nothing in the top 10 % or the bottom 15 % (player interface).

## 5. Voice-over

- **You record the voice** (French and English). There is no speech synthesis in PathProof; a synthetic voice for the narration is possible but must be disclosed in the video description.
- Close microphone (15 cm), quiet room, pop filter or, failing that, a cloth in front of the microphone. WAV 48 kHz mono, one file per block: `video/raw/VO_en_V1.wav` … `VO_en_V6.wav`, likewise `VO_fr_*`.
- Read in a calm voice, 2 takes per block, cut loud breaths. Numbers are spoken in full (this is how they are written in the scripts).
- The text is constrained by the windows above: if a sentence is too long to say, shorten it **in the script** (not by speeding up the voice), then tell the montage.
- The voice of the sample voice notes is synthetic (`data/samples/README.md`). A caption on screen "fictional student · synthetic voice" in S05 says so.

## 6. Montage (code agent, `ffmpeg`)

Prerequisite: `ffmpeg` and `ffprobe` installed (absent from this machine on 3 Nov: `sudo apt install ffmpeg`).

A file `video/timeline.csv` describes the montage, one line per shot: `shot, source, in, out, speed, zoom, card, voice_block`. The montage is replayed from this file if a take changes.

Steps, in order:
1. **Footage check**: `ffprobe` (resolution, fps, duration). Set aside whatever does not meet §4.
2. **Voice**: light noise reduction, normalization to **−16 LUFS** integrated, true peak −1 dBTP; the blocks are placed at their window.
3. **Shots**: cut (`in`/`out`), speed-up of the waits with a "×3" or "×4" badge always visible, targeted zoom (`crop` + `scale`) on the model badges, on the question, on the opened proof.
4. **Cards**: S03, S13 (SAM caption) and S16, sober, system fonts, interface colours (dark theme, PathProof green).
5. **Subtitles**: `pathproof_en.srt`, cues from `script-en.md` (2 lines maximum, 42 characters horizontal, 28 vertical), timed on the recorded voice. For the French-voice version: the **same English cues**, retimed on the French audio.
6. **Sound**: no music with lyrics; a discreet background (−30 dB) is allowed, otherwise nothing. The voice-note excerpt of S01 goes to −22 dB under the voice.
7. **Export**:
   - YouTube: H.264 High, 1920×1080, 30 fps, CRF 18, AAC 192 kbit/s; subtitles as an **`.srt` track** to upload with the video.
   - X vertical: H.264, 1080×1920, 30 fps, CRF 20, AAC 192 kbit/s; subtitles **burned in** (`subtitles=` with `force_style`, larger font).
8. **Check**: `ffprobe` gives a duration ≤ 180.0 s for each file; full playback; `ffmpeg -i … -af ebur128` to check the level; a clean first frame for the thumbnail.

The montage must not make anything look better than reality: no fake trace, no retouched report, no value recomputed by hand.

## 7. Honesty rules (criteria of issue #39)

| Criterion | How it is met |
|---|---|
| 3:00 at most, English subtitles | 2:58; `.srt` or burned in, even on the French voice |
| PRD §13 sequence | blocks V1 to V6, windows of §3 |
| Every shot = a real run, recorded mode stated | only the cards S03, S13 (SAM caption) and S16 are not runs and read as cards; a "recorded" take is stated in the voice |
| No key, real data or unsourced figure | fictional data only; 77,101 sourced on screen; the guide PDF is not shown (only the rows cited by the proofs are) |
| Link openable without login | public or unlisted video; opened in a private window before being put in the README |
| Only work done during the event | neither the WhatsApp V1 nor old captures; the repository is the hackathon's |

Vocabulary points: never "chatbot"; "verified" only for a report whose every claim passed `verify_report`; "eleven compliant cases, one pass each" (not "reliable").

**Gap with the PRD, stated in the voice:** the PRD (§3.1, line 97, and the case table of §10) says that Pharmacie, dropped by the quality check, is **listed** under "Ce que je n'ai pas pu vérifier" ("what I could not verify"). In the real output (`evals/results/2026-11-03/unverified_trap.json`), the report does not mention Pharmacie and writes "Toutes les affirmations ci-dessus sont vérifiées" ("All the claims above are verified"); the row is only visible as an **excluded** row in the `lookup_filieres` result. The voice of block V5 therefore says "excluded", not "listed as unverified". See `docs/decisions.md`.

## 8. Schedule (Tuesday 3 November, freeze in the evening; submission limit: 4 November 21:00 ET = 5 November 03:00 in Porto-Novo)

| Step | Estimated duration | Output |
|---|---|---|
| 1. Install `ffmpeg`; set up OBS and the window; 1-minute test | 30 min | clean test footage |
| 2. Takes T1 to T5, English interface, horizontal screen | 60 min | `video/raw/S*_en_desktop_*` |
| 3. English voice, blocks V1 to V6 | 30 min | `VO_en_*.wav` |
| 4. Montage P1 (English YouTube) + `.srt` | 60 to 90 min | `pathproof_youtube_en.mp4` |
| 5. Check: duration, level, full playback, opening in a private window | 20 min | list checked on the issue |
| 6. Vertical takes + montage P2 (X) | 60 min | `pathproof_x_en_vertical.mp4` |
| 7. French version P3 (FR takes, FR voice, montage) | 90 min | optional |
| 8. Upload, link in the README, X post (E7.3), submission (E7.5) | 30 min | links |

The margin of the night of 4 to 5 November is for retakes, not for new things.

## 9. To provide yourself

- `{{X_HANDLE}}`: the X account shown on the S16 card (no account to cite was available).
- Title and description of the video (the description cites: demo, repository, "fictional data", synthetic voice of the sample notes).
- The final video link: to add afterwards in the README.
- The choice of voice: yours or a disclosed synthetic voice.
