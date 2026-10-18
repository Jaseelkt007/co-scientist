// Co-Scientist orchestration as a deterministic Workflow (optional, heavy-parallel path).
// Run via the Workflow tool ONLY when the user opts into multi-agent orchestration.
//   Workflow({ scriptPath: ".../scripts/coscientist_workflow.js", args: { goal, criteria, rounds, fanout } })
// Scripts have NO filesystem access, so state is in-memory and RETURNED; the main thread persists it
// into the run directory (see references/memory-schema.md). Elo is computed in-script (start 1200, K=32).

export const meta = {
  name: 'co-scientist',
  description: 'Generate, review, Elo-tournament, and evolve hypotheses across rounds, then synthesize.',
  phases: [
    { title: 'Configure' },
    { title: 'Generate' },
    { title: 'Reflect' },
    { title: 'Rank' },
    { title: 'Evolve' },
    { title: 'Meta-review' },
    { title: 'Synthesize' },
  ],
}

const goal = (typeof args === 'object' && args && args.goal) ? args.goal : String(args || '')
const ROUNDS = (args && args.rounds) || 3
const FANOUT = (args && args.fanout) || 4
let criteria = (args && args.criteria) ||
  'Alignment, Plausibility, Novelty (grounded in prior work), Testability, Safety'

const HYPS = { type: 'object', properties: { hypotheses: { type: 'array', items: { type: 'object',
  properties: { summary: { type: 'string' }, category: { type: 'string' }, text: { type: 'string' } },
  required: ['summary', 'text'] } } }, required: ['hypotheses'] }
const REVIEW = { type: 'object', properties: { verdict: { type: 'string', enum: ['pass', 'reject'] },
  correctness: { type: 'number' }, novelty: { type: 'number' }, quality: { type: 'number' },
  critique: { type: 'string' } }, required: ['verdict', 'critique'] }
const VERDICT = { type: 'object', properties: { winner: { type: 'number', enum: [1, 2] },
  rationale: { type: 'string' } }, required: ['winner'] }
const TEXT = { type: 'object', properties: { text: { type: 'string' } }, required: ['text'] }

const fb = () => metaFeedback ? `\n\nMeta-review feedback to apply:\n${metaFeedback}` : ''
let metaFeedback = ''
let hyps = []           // {id, summary, text, category, elo, parents, origin, review}
let nextId = 1
const add = (h, origin, parents = []) =>
  hyps.push({ id: 'h' + (nextId++), elo: 1200, parents, origin, review: null, ...h })
const E = (a, b) => 1 / (1 + 10 ** ((b - a) / 400))

phase('Configure')
log(`goal: ${goal.slice(0, 80)}…  rounds=${ROUNDS} fanout=${FANOUT}`)

for (let r = 1; r <= ROUNDS; r++) {
  // ---- Generate (barrier: collect this round's fresh ideas) ----
  const gen = await parallel(Array.from({ length: FANOUT }, (_, i) => () =>
    agent(`You are the Generation agent (strategy #${i + 1}: vary between literature-grounded, debate/self-play, `
      + `assumption-decomposition, and out-of-the-box). Propose 1-3 novel, testable hypotheses for the goal.\n`
      + `Goal: ${goal}\nCriteria: ${criteria}${fb()}`,
      { phase: 'Generate', label: `gen:r${r}:${i + 1}`, schema: HYPS })))
  gen.filter(Boolean).flatMap(g => g.hypotheses).forEach(h => add(h, `generation:r${r}`))

  // ---- Reflect (pipeline: each unreviewed hypothesis reviewed independently) ----
  const fresh = hyps.filter(h => !h.review)
  const reviews = await pipeline(fresh,
    h => agent(`You are the Reflection agent. Rigorously review this hypothesis against the criteria; do an `
      + `initial check, then assess correctness, novelty (vs. prior work), quality, and safety. Reject flawed `
      + `or non-novel ideas.\nGoal: ${goal}\nCriteria: ${criteria}\nHypothesis: ${h.text}${fb()}`,
      { phase: 'Reflect', label: `rev:${h.id}`, schema: REVIEW }))
  fresh.forEach((h, i) => { h.review = reviews[i] || { verdict: 'pass', critique: '' } })
  hyps = hyps.filter(h => h.review.verdict !== 'reject')

  // ---- Rank (Elo tournament; pair each hypothesis with its neighbor by current Elo) ----
  const ranked = [...hyps].sort((a, b) => b.elo - a.elo)
  const pairs = []
  for (let i = 0; i + 1 < ranked.length; i += 2) pairs.push([ranked[i], ranked[i + 1]])
  const verdicts = await parallel(pairs.map(([a, b], i) => () => {
    const top = i < 2 // top pairs get the richer multi-turn debate
    return agent(`You are the Ranking agent running an Elo tournament match. ${top
      ? 'Conduct a multi-turn scientific debate, then decide.' : 'Do a concise comparison, then decide.'}\n`
      + `Goal: ${goal}\nCriteria: ${criteria}\nHypothesis 1: ${a.text}\nReview 1: ${a.review.critique}\n`
      + `Hypothesis 2: ${b.text}\nReview 2: ${b.review.critique}\nConclude which is better.`,
      { phase: 'Rank', label: `match:${a.id}v${b.id}`, schema: VERDICT })
      .then(v => ({ a, b, v }))
  }))
  for (const res of verdicts.filter(Boolean)) {
    const { a, b, v } = res
    const sa = v.winner === 1 ? 1 : 0
    const ea = E(a.elo, b.elo)
    a.elo = Math.round((a.elo + 32 * (sa - ea)) * 10) / 10
    b.elo = Math.round((b.elo + 32 * ((1 - sa) - (1 - ea))) * 10) / 10
  }

  // ---- Evolve (refine the current top hypotheses into NEW contenders) ----
  const top = [...hyps].sort((a, b) => b.elo - a.elo).slice(0, Math.min(3, hyps.length))
  const evolved = await parallel(top.map((h, i) => () =>
    agent(`You are the Evolution agent (strategy: ${['feasibility', 'grounding', 'combination/out-of-box'][i % 3]}). `
      + `Create a NEW improved hypothesis (do not edit the original).\nGoal: ${goal}\nCriteria: ${criteria}\n`
      + `Source hypothesis: ${h.text}${fb()}`,
      { phase: 'Evolve', label: `evo:${h.id}`, schema: HYPS }).then(g => ({ g, parent: h.id }))))
  evolved.filter(Boolean).forEach(({ g, parent }) =>
    g.hypotheses.forEach(h => add(h, `evolution:r${r}`, [parent])))

  // ---- Meta-review (synthesize critique → feedback appended to all agents next round) ----
  const mr = await agent(`You are the Meta-review agent. Synthesize recurring critique patterns across these `
    + `reviews into actionable, forward-looking guidance for future generation/review/ranking/evolution.\n`
    + `Goal: ${goal}\nReviews:\n${hyps.map(h => `- ${h.id}: ${h.review?.critique || ''}`).join('\n')}`,
    { phase: 'Meta-review', label: `meta:r${r}`, schema: TEXT })
  metaFeedback = mr ? mr.text : metaFeedback
  log(`round ${r}: ${hyps.length} live hypotheses, top Elo ${Math.max(...hyps.map(h => h.elo)).toFixed(0)}`)
}

phase('Synthesize')
const finalRanked = [...hyps].sort((a, b) => b.elo - a.elo)
const overview = await agent(`You are the Meta-review agent. Write a research overview: Main Research `
  + `Directions, then per direction give Rationale, Recent Findings, and Areas of Research `
  + `(Why / What / Example Idea).\nGoal: ${goal}\nTop hypotheses:\n`
  + finalRanked.slice(0, 8).map(h => `- [${h.elo.toFixed(0)}] ${h.summary}: ${h.text}`).join('\n'),
  { phase: 'Synthesize', label: 'overview', schema: TEXT })

return {
  goal,
  ranked: finalRanked.map(h => ({ id: h.id, elo: h.elo, summary: h.summary, category: h.category,
    text: h.text, origin: h.origin, parents: h.parents })),
  meta_review: metaFeedback,
  research_overview: overview ? overview.text : '',
}
