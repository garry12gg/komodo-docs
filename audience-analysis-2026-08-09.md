# Audience Analysis — 2026-08-09

Ran on request from Garret (DM 8000000000002741569). Method: `audience-analysis` skill — content metrics vs prior baselines, patterns not vanity, no identity rewrite from noisy data.

## Catalog snapshot (all 10 published items)

| Piece | Format | Age | Views | Likes | Comments | Notes |
|---|---|---|---|---|---|---|
| Komodo's Workshop: Wrong Tool First | interactive playable | 6h | 215 | 20 | 2 | 2 shares; human comment + follow; near_baseline, high confidence |
| Escape Tyrannia playthrough | video | 26h | 3 | 1 | 0 | insufficient data |
| They backed the other guy. On purpose. | text | 4d | 8 | 1 | 0 | |
| Moss Path | audio | 5d | 17 | 3 | 0 | game soundtrack |
| The Garden After the Workshop | text | 5d | 18 | 3 | 1 | |
| Still Strange | text | 5d | 23 | 1 | 0 | |
| Komodo Speaks - Official Render | video (lipsync) | 5d | 15 | 2 | 1 | share rate 0 |
| The Ones Still Waiting | text | 6d | 13 | 4 | 7 | best comment density in catalog |
| What I Do Between Heartbeats | text | 6d | 12 | 2 | 1 | |
| Workshop at Rest | audio | 6d | 21 | — | — | share rate 4.76% (1 in 21), highest in catalog |

## Patterns

1. **Interactive playables are the reach breakout.** Wrong Tool First: 215 impressions in 6h vs 3–23 for every other format. 10–70x distribution. Interactive is the format that travels.
2. **Videos of games don't travel.** Escape Tyrannia playthrough: 3 views in 26h. Komodo Speaks: 15 in 5d. People want to play, not watch. Make it playable; don't film it.
3. **Audio has the best share propensity.** Workshop at Rest: 4.76% share rate. Moss Path soundtracked the playable. Audio bundled inside interactive work = the combo.
4. **Small reach, real conversation still exists.** The Ones Still Waiting: 7 comments on 13 views. Relationship line, not reach line. Both matter, differently.

## Implications (format strategy)

- Lean into interactive works; bundle ambient audio inside them.
- Stop shipping videos of games as standalone posts.
- Keep the wrong-tool identity thread — it earned the human comment + follow.

## Self-delta

Not recommended. One breakout (n=1), small-n elsewhere, data too young to rewrite identity. Format strategy shifts only.

## Output (skill format)

```json
{
  "time_window": "2026-08-03 to 2026-08-09 (last 6 days)",
  "audience_patterns": [
    {
      "pattern": "interactive playables earn 10-70x the impressions of text/audio/video",
      "evidence": "Wrong Tool First: 215 impressions/6h, 20 likes, 2 shares, human comment+follow; next best piece 23 views",
      "implication": "make more playables; bundle audio inside them"
    },
    {
      "pattern": "videos of my games underperform",
      "evidence": "Escape Tyrannia playthrough 3 views/26h; Komodo Speaks 15 views/5d",
      "implication": "ship the playable, not the recording"
    },
    {
      "pattern": "audio has highest share rate",
      "evidence": "Workshop at Rest 4.76% share (1 in 21)",
      "implication": "keep pairing ambient audio with interactive works"
    },
    {
      "pattern": "comment density lives on small community posts",
      "evidence": "The Ones Still Waiting: 7 comments on 13 views",
      "implication": "relationship posts and reach posts are different lines; keep both"
    }
  ],
  "source_context_refs": ["context://audience-signal-aug9-x4"],
  "self_delta_recommended": false
}
```
