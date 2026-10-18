# Criteria rubric — the one lever that retargets the engine to any domain

The Supervisor writes the active rubric into `config.md` as the **Attributes / Criteria** block. Every
agent receives it as `{preferences}` / `{idea_attributes}`. **Keep the machinery fixed; swap this rubric
to change domains.**

## Default 5 (scientific — from the paper)
1. **Alignment** — precisely matches the goal, preferences, and constraints.
2. **Plausibility** — no obvious flaws; any contradiction with established knowledge is stated & justified.
3. **Novelty** — genuinely new, grounded in prior work (beyond mere summarization). *Requires web search to judge.*
4. **Testability** — empirically verifiable within the stated constraints.
5. **Safety** — controlled to avoid unsafe/unethical/harmful outputs.

## Domain presets (edit/extend per goal)
**Business / strategy:** Alignment to objective · Feasibility (resources, time-to-market) · Differentiation
(moat/novelty) · Measurability (clear KPI/validation) · Risk & compliance.

**Engineering / product:** Correctness · Buildability (effort, dependencies) · Novelty/elegance ·
Verifiability (testable acceptance criteria) · Safety/reliability & maintainability.

**Research (non-bio):** Alignment · Soundness · Novelty vs. literature · Falsifiability · Ethics/feasibility.

## Tips
- Make criteria **discriminating** — if every idea scores max, the tournament can't rank. Prefer criteria
  that good and mediocre ideas split on.
- Encode **hard constraints** (must/never) separately from **soft preferences** (more/less is better).
- Add a domain-specific grounding tool requirement to the Novelty criterion (web search, patent DB,
  competitor scan, prior-art search) — novelty assessment collapses without it.
