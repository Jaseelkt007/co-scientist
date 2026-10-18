# co-scientist — a Claude Code plugin

A Claude Code plugin that replicates Google's **AI Co-Scientist**: a **team of specialized subagents** that
**generate → review → Elo-tournament → evolve → synthesize** novel ideas for a hard, open-ended goal.
It is **domain-agnostic** (science, business, engineering, product, strategy) and its quality **scales
with the number of rounds** you let it run.

## Install

```
/plugin install co-scientist --marketplace Jaseelkt007/co-scientist
```

Or in two steps (inside Claude Code, or prefix with `claude` in your shell):

```
/plugin marketplace add Jaseelkt007/co-scientist
/plugin install co-scientist@jaseel-plugins
```

Requires Python 3 on your `PATH` (the Elo bookkeeping script uses only the standard library).
Update later with `/plugin marketplace update jaseel-plugins`.

### Want ideas *measured*, not just argued? → `co-scientist-lab`

The same marketplace has **[co-scientist-lab](https://github.com/Jaseelkt007/co-scientist-lab)**: this
engine plus an Experiment agent that runs each idea through your project's own command (training run,
benchmark, test suite), asks a few setup questions (command, metric, target, rounds), and loops until the
target is hit or the round budget is spent.

```
/plugin install co-scientist-lab@jaseel-plugins
```

---

## 1. The fastest way to use it

Describe a hard, open-ended goal in natural language. The skill triggers on phrasings like:

- "run co-scientist on **<goal>**"
- "generate and tournament-rank hypotheses for **<goal>**"
- "find a novel approach / strategy / mechanism for **<goal>**"
- "brainstorm then stress-test ideas for **<goal>**"

Or invoke it directly: `/co-scientist:co-scientist <goal>`.

**Examples**
- `run co-scientist on: how can our SaaS cut first-week churn for free-trial users?`
- `find a novel mechanism that could explain <X> in my field, and rank the candidates`
- `co-scientist: best go-to-market wedge for a new AI note-taking app, 3 rounds`

A good goal includes **constraints and preferences** (budget, audience, what counts as success, what to
avoid). The more specific the goal, the sharper the criteria — and the criteria are what the tournament
judges on.

## 2. What happens when it runs

1. **Supervisor** parses your goal into a *research plan configuration* (`config.md`) — the criteria a
   strong idea must meet. **It will show you this and ask you to confirm** before round 1.
2. Each **round**: Generation proposes ideas → Reflection peer-reviews and filters them → Proximity
   clusters/dedupes → Ranking runs an **Elo tournament** (debates for top pairs) → Evolution refines the
   leaders into new contenders → Meta-review distills lessons that are fed back into every agent next round.
3. It stops at your iteration cap (or when the top ideas stop improving) and hands you a **ranked list +
   a research overview** (directions, rationale, concrete next experiments).

All shared state is written to files under `.coscientist_runs/<your-goal-slug>/` in your project (see
[`skills/co-scientist/references/memory-schema.md`](skills/co-scientist/references/memory-schema.md)), so a
run can be paused and resumed.

## 3. The one knob that matters: rounds (test-time compute)

The core finding of the paper is **more rounds = better ideas**. So:
- **Quick pass:** "1 round, a few ideas" — fast sanity check.
- **Thorough:** "run ~5 rounds with wide generation" — better, costs more tokens/time.

You can say the number of rounds in your request, or let it decide and stop on plateau.

## 4. Retargeting to any domain

The machinery never changes — only the **criteria** do. To move from medicine to business/engineering,
the Supervisor swaps the rubric in `config.md` (presets live in
[`skills/co-scientist/references/criteria.md`](skills/co-scientist/references/criteria.md)). That's the
whole "domain-agnostic" trick.

## 5. Expert-in-the-loop (you stay in control)

- Confirm/edit the parsed criteria before round 1.
- At any point: refine the goal, **add your own idea** (it enters the tournament at Elo 1200), or give a
  manual review (it feeds ranking + evolution).
- At the end: you pick which top-ranked ideas to actually pursue.

## 6. Heavy / deterministic mode (optional)

For a large, highly-parallel run there's a Workflow script at
[`skills/co-scientist/scripts/coscientist_workflow.js`](skills/co-scientist/scripts/coscientist_workflow.js)
(uses Claude Code's `Workflow` tool). It fans out generation, reflection, ranking, and evolution across many
subagents per round. Only use it when you explicitly want multi-agent orchestration, since it can spawn
many agents and use a lot of tokens.

## 7. Files you'll get per run (`.coscientist_runs/<slug>/`)

| File | What it is |
|---|---|
| `config.md` | the parsed criteria/constraints (the rubric) |
| `hypotheses.json` | every idea, with Elo, parents, status |
| `reviews/<id>.md` | accumulated peer reviews per idea |
| `tournament.json` | Elo ratings + match history + proximity graph |
| `meta_review.md` | the round-over-round feedback that improves every agent |
| `research_overview.md` | the final synthesis handed to you |

## Repository layout

```
.claude-plugin/
  plugin.json          plugin manifest
  marketplace.json     the jaseel-plugins marketplace (lists co-scientist and co-scientist-lab)
skills/co-scientist/
  SKILL.md             orchestration instructions
  agents/              subagent personas (supervisor, generation, reflection, ranking, ...)
  references/          architecture, criteria presets, memory schema
  scripts/             elo.py (state + Elo bookkeeping), coscientist_workflow.js
```

### Developing locally

```bash
claude plugin validate .
claude --plugin-dir .      # load this checkout for one session without installing
```

## Provenance

Based on *Towards an AI co-scientist* (Gottweis et al., [arXiv:2502.18864](https://arxiv.org/abs/2502.18864);
Nature 2026). Agent prompts follow the authors' published prompts where available; the rest are
reconstructed in-style and labeled as such in `skills/co-scientist/agents/`. This is an independent
replication, not affiliated with Google.

## License

MIT — see [LICENSE](LICENSE).
