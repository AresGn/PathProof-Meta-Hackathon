# Public deployment on Vercel (E5.4, #33)

A single Vercel project, production = `main`, redeployed on every push. No staging, no Docker.

## Configuration
| Item | Value |
|---|---|
| Entry point | `app.py` (root): re-exports `app` from `src/api/server.py` |
| Included files | `vercel.json`: `web/**` and `data/**` (without `data/source/**`, the guide PDF is never deployed) |
| Maximum duration | 300 s (`maxDuration`, the Hobby plan ceiling); the SSE stream stays open for the whole run |
| Disk | Only `/tmp` is writable: `new_run_tmpdir` uses it when `VERCEL` is set (the student's uploads there are deleted after the run or after 30 min) |
| Project | `.vercel/` is ignored by git (local identifiers) |

## Environment variables
- `MUSE_API_KEY`: entered in Vercel (dashboard), never in the repository. It is set for Production **and** Preview: previews are therefore protected by the Vercel login (302 verified on a deployment URL and on the branch alias), only the production domain is public.
- `MUSE_BASE_URL`: only if different from `https://api.meta.ai/v1`.

## Usage limit per IP
Vercel Firewall rule on `POST /run` and `POST /answer`: **5 requests per minute per IP**, beyond that a **429** response before reaching the function (so no API cost). A full run = 1 `/run` + at most 2 `/answer`. Counters are per region: several regions can add up to N times the threshold. The server also keeps its own internal ceilings (5 simultaneous runs, 100 suspended sessions).

Command: see the "Verification" section below for the proof of the 429.

## Spending
The Vercel plan is Hobby, with no card: Vercel bills nothing (an exceeded quota blocks the service), so no Vercel spending alert is useful. The real cost is that of the Meta credits consumed by each run; it is bounded by the per-IP limit above, by the 5 simultaneous runs and by the **Meta spending alert** (Billing), enabled on day one by the key owner (E0.2, #4).

## Accepted limit: `ask_student` sessions
`PendingRunStore` is in memory. On Vercel, `/answer` may land on a different instance than `/run`: a 404 response, the page restores the trace and closes the session (the E5.3 recorded run does not replace this case, by choice: see `docs/decisions.md`). A shared store is not set up before the 3 Nov freeze.

## Voice: ffmpeg
A Vercel function has no `ffmpeg`: `transcribe_voice` was failing in production ("ffmpeg is not installed"). `src/clients/voice.py` uses the system `ffmpeg` if there is one, otherwise the binary bundled by `imageio-ffmpeg` (in `requirements.txt`). Verified on the public URL: 3 transcriptions out of 3 succeeded.

## Measurements on the public URL (3 Nov 2026)
- Full run (serie D sheet + matching voice note): `done` / `ok` in 164 s in total, verified report of 4,050 characters, SSE stream delivered step by step; `/run` alone 22 to 60 s, `/answer` up to 190 s, each under the 300 s limit.
- `/answer`: 200 in 5 attempts out of 6; **one 404** (session lost between instances), in line with the limit above. The observed rate is not zero: if the video demo hits it, record on the local page or move to a shared store.
- One attempt reached the 12-step limit without a report (the model kept repeating `verify_report`): agent behaviour (E6.3), not hosting.
- Per-IP limit: 5 `POST` requests answered 200, then 3 answered 429, over 8 calls.

## Verification (to replay from another network)
```bash
URL=https://<project>.vercel.app
curl -s $URL/health
curl -s $URL | grep -c MUSE           # 0
for f in $(curl -s $URL | grep -o 'js/[a-z-]*\.js'); do curl -s $URL/$f | grep -c MUSE; done   # 0
for i in $(seq 1 8); do curl -s -o /dev/null -w "%{http_code}\n" -X POST $URL/run -F text=bonjour; done   # 429 beyond the threshold
```

## Freeze
No deployment after the freeze on the evening of 3 Nov. Rollback: `vercel rollback` or promote the previous deployment from the dashboard.
