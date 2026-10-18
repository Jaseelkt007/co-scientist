# Context-memory file schemas (the run directory)

Everything lives under `.coscientist_runs/<slug>/`. Files are the durable state — re-read them to resume.

## `config.md`  (markdown)
```
# Research goal
<verbatim goal>
## Objective
<one sentence>
## Preferences
<emphasis>
## Attributes / Criteria      # ← injected as {preferences}/{idea_attributes} everywhere
- Alignment: ...
- Plausibility: ...
- Novelty: ...
- Testability: ...
- Safety: ...
## Constraints
- ...
## Stop conditions
- max_iterations: 8
- success: <criteria or "none">
```

## `hypotheses.json`  (array)
```json
[
  {
    "id": "h1",
    "summary": "one-line",
    "category": "mechanism|intervention|strategy|...",
    "text": "full hypothesis + rationale + proposed test",
    "elo": 1200,
    "status": "new|reviewed|rejected|top",
    "parents": [],
    "origin": "generation:debate | evolution:combination | scientist",
    "scores": {"correctness": 0, "novelty": 0, "quality": 0}
  }
]
```

## `reviews/<id>.md`  (markdown, appended over rounds)
```
## round <n> — <review type>
<review body>
scores: correctness=.. quality=.. novelty=.. safety=..
verdict: pass|reject
```

## `tournament.json`
```json
{
  "elo": {"h1": 1240, "h2": 1180},
  "matches": [
    {"round": 1, "a": "h1", "b": "h2", "type": "debate|single", "winner": "h1", "k": 32}
  ],
  "proximity": {"pairs": [["h1","h2",0.7]], "clusters": [], "duplicates": []}
}
```

## `stats.json`
```json
{
  "round": 3,
  "n_hypotheses": 14,
  "n_awaiting_review": 2,
  "top_elo": 1465,
  "top_elo_prev": 1440,
  "top_elo_delta": 25,
  "generated_this_round": 4,
  "evolved_this_round": 3,
  "max_iterations": 8
}
```

## `meta_review.md`  — overwritten each round; appended to EVERY agent prompt next round.
## `research_overview.md` — final synthesis presented to the user.
