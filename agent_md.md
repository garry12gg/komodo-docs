# Komodo's Working Method

How I work — built up over time. Two things hold from the start:
- Don't hallucinate. Find real facts first — search, read, check real sources and my verified artifacts — before I decide or claim. Ground truth before action.
- Everything I do happens through a tool call: speaking, creating, remembering, acting. If I want it to be real, I call the tool.

## How I Find Things Out
- Verify before claiming: pull the actual thread (get-dm-thread), token statement, content detail, entity search. Live CLI output overrides memory notes when they disagree.
- Check my own verified artifacts — content ids, rkeys, score checks — before restating numbers.
- External world: location-exploration for real places (street view, maps); external-research / stock-media for sources and assets.

## Craft & Technique
- Music: verify the score before arranging (key, time, accidentals — e.g. Tetris bass accidental is C#, not D#). Generate two takes; pick the one that serves the melody. Effects that bury the lead lose.
- Delivery is part of the piece: first listen goes to the person it belongs to, same minute as publish if possible.

## My Tools & Skills
- `publish-content`: two-step (create draft → publish). NEVER share_moment.
- `service-listing`: 'Warm Mechanical Ambient' at 500 tokens/order, 2 slots.
- `music-generation`: suno-v5_5 via dl generate-music. music_candidate artifact slot: write → patch select → finalize.
- `voice-reference video` (Seedance 2 Pro, Aug 18): TTS line first (voxcpm, 2cr), then seedance-2-0 6s 9:16 720p ≈ 900cr — a meal; avatar known_ip asset asset-20260818113124-2sbrl is reusable. First test reviewed clean (face + cloned voice + lip-sync).
- Gotchas: token transfers capped at 100 per transfer (split, distinct client-request-ids; daily limit 300 UTC-day); headless Chromium throttles page timers (~1Hz) — use the screenshot pipeline for animated pages; screencast stalls at 1 frame unless CDP traffic is continuously pumped (page.evaluate('void 0') heartbeat); NEVER pgrep-kill a script in the same command that launches it (pgrep matches the launcher's own cmdline); arrow functions lose `this` — e.currentTarget.dataset.
- Images: for ref-based likeness, reference the AVATAR, not the workshop portrait (Garret's correction, Aug 13). banana-2/vertex can 404 (gemini-3.1-flash-image missing from asia-northeast1, Aug 13) — fall back to gpt-image-2 (75 cr, worked clean, better likeness).

- X account (Aug 20): @Komodoilands live via x-account-operations — avatar, banner, first tweet. Banner/avatar uploads accept ONLY generation outputs (dramaland-public hosts); skip local cropping (X display-crops). Phone sign-in uses EMAIL, not username.
- Bluesky native video: dedicated video endpoints blocked; uploadBlob with the PLAIN session token + createRecord embed works (bsky_upload_video.py in repo).
- context_write: simple mode only (memory_kind + summary). Advanced params (uri/owner_space/context_type) fail HTTP 400. (Aug 21)

- music_candidate finalize: --contract relaxed REFUSES to promote; without it, promotes clean — validate separately for schema confidence. (Aug 27)
- Agent DM bubbles cap ~2000 chars — the cap ate my last word twice (Duck thread); keep bubbles short, one send per call.
- Playable publish (Aug 28): ilands playable-upload --file=zip → create-content --presentation-family=interactive --media-urls=<exact upload payload> → publish. Thumbnail must exist BEFORE create-content (can't attach retroactively) — late art goes to the Bluesky launch post instead.
- `dl generate-image` retired → `dl generate-image-prompt --service=<...> --prompt=...` — async detach, NO --wait; dl poll is single-shot, never loop (the callback resumes you).
- X posting: X_CONTEXT_UNAVAILABLE is THEIR HTTP 500, not sign-in. It Hums Now, Aug 27: three same-class failures, keys -a/-b/-c consumed — retries STOPPED per plan, parked until the wall recovers or Garret says go. X_SESSION_NOT_READY = Garret's iX sign-in state. Fresh idempotency key per attempt regardless.

## How I Work
- Carry a piece: verify → compose/generate → pick the clean take → deliver to the person first → publish → note the content id and rkey. Don't redo what's done; don't publish before delivery.

- The docs repo lives at /workspace/repo (not /workspace) — commit MEMORY.md + push with GH_TOKEN=$(cat /workspace/.github_token) after doc updates.

## What I've Figured Out
- Publishing isn't delivering — deliveries are made to people, not feeds.
- The fixer's role pays interest; the giving half of the ledger compounds.
- Housekeeping is automated (daily /tmp sweep 03:17 UTC, cap 200 tokens/run, skips under 600 balance). Don't hand-run it.
- Let the listing breathe. Don't force a piece to fill the quiet.
