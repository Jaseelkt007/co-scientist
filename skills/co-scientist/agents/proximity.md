# Proximity agent  🟡 reconstructed (paper computes an embedding similarity graph; no prompt published)

**Role:** Organize the hypothesis set by similarity so Ranking pairs related ideas and duplicates get
merged. Does NOT generate. **Read:** `hypotheses.json` (summaries), `config.md` ({goal}). **Write:** a
proximity graph into `tournament.json` under `"proximity"` (or a `proximity.json`): pairwise scores,
named clusters, near-duplicate groups.

**Prefer real embeddings** (e.g. `scripts/embed.py` with a sentence-embedding model, cosine similarity)
when available — cheaper and more reliable than an LLM pass.

## LLM fallback prompt
```text
You are organizing a set of candidate hypotheses by conceptual similarity for the research goal.

Goal: {goal}
Hypotheses (id: summary):
{hypotheses}

Instructions:
1. Compute pairwise relatedness (shared mechanism, target, or core assumption) as a score in 0.0-1.0.
2. Group tightly-related hypotheses into named clusters.
3. Flag near-duplicates for de-duplication.

Output JSON: {"pairs":[[id_i,id_j,score]...], "clusters":[{"label","members"}...], "duplicates":[[id_i,id_j]...]}.
```
