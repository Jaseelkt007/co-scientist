# Architecture summary (self-contained)

Faithful replica of Google's AI Co-Scientist (Gottweis et al., Nature 2026; arXiv:2502.18864). Full
write-ups live at the project root: `coscientist_architecture.md` (blueprint) and `coscientist_prompts.md`
(verified prompt library). This file keeps the skill self-contained.

## The loop
```
goal ──(Supervisor parse)──▶ config (criteria) ─┐
                                                 ▼
   ┌─────────────────── round (repeat until terminal) ───────────────────┐
   │  Generation → new hypotheses (Elo 1200)                              │
   │  Reflection → reviews; filter flawed/non-novel                       │
   │  Proximity  → similarity graph (cluster + dedupe)                    │
   │  Ranking    → Elo tournament: similar/new/top paired;               │
   │               top→multi-turn debate, low→single-turn; update Elo     │
   │  Evolution  → NEW refined hypotheses (re-enter tournament)           │
   │  Meta-review→ critique appended to ALL agents next round             │
   │  Supervisor → stats; terminate on stats OR max iterations            │
   └─────────────────────────────────────────────────────────────────────┘
                                                 ▼
        Meta-review → ranked hypotheses + research overview → scientist
```

## Invariants to keep (faithfulness)
- New & evolved hypotheses start at **Elo 1200**; Evolution never edits winners (creates new contenders).
- Meta-review feedback is **prompt-appended**, not fine-tuned ("learning without back-propagation").
- **Novelty/full reviews require web search.** Match-making prefers similar + new + top hypotheses.
- **Quality scales with rounds** (test-time compute) — there is no fixed "answer in one shot."

## Key numbers (from the preprint)
Initial Elo 1200 · top-Elo answers reach 78.4% top-1 on GPQA diamond · validated over 203 research goals ·
Elo rises monotonically with compute (no saturation). K-factor not stated → default 32.
