# Mechanism evals

Quantitative eval harness for the `/hooks/memories` extract-queries step.

## Why

The extract-queries prompt asks Qwen to turn a conversational message into a
list of search queries that get embedded and recalled against `cortex.memories`.
Issue [#13] documents the dominant failure mode: when a prompt has multiple
substantive topics, Qwen sometimes commits to one and silently drops the
others. We need to measure this quantitatively before iterating on the prompt
or extending the pipeline (e.g. an `/hooks/asides` companion).

## Shape

- **dataset**: hand-curated conversational prompts pulled from our
  conversation history (Jeffery's real prompts, not synthetic), each labeled
  with the topics the extract step *should* surface.
- **scoring**: for each labeled topic, mark a hit if any extracted query has
  cosine similarity above τ against the topic string (Qwen 3 Embedding 4B,
  same model production uses).
- **stratification**: cases are bucketed by topic-count so per-stratum scores
  surface improvements on the multi-topic failure mode that aggregate scores
  would dilute.

Three strata:

| Tag | Meaning | Count |
|---|---|---|
| `S` | single substantive topic (baseline — is recall working at all?) | 7 |
| `M` | multi-substantive (the failure-mode stratum) | 12 |
| `P` | primary-topic + peripheral references (the should-filter stratum) | 6 |

## Layout

```
evals/
├── README.md              ← this file
├── seed_cases.yaml        ← committed: source-database row ids + hand-curated labels
├── extract_dataset.py     ← committed: seed_cases.yaml + source DB → data/dataset.yaml
├── prompts/
│   └── v1-baseline.md     ← committed: snapshot of the current production prompt
└── data/                  ← gitignored: real prompt content + scoring results
    ├── dataset.yaml
    └── results.db
```

`seed_cases.yaml` (committed) holds the row ids and labels — enough to
reconstruct the dataset on any machine with source-DB access.
`data/dataset.yaml` (gitignored) holds the materialized content — real
conversational prompts from our history, pulled from a private DB.

## Bootstrap

From the repo root:

```sh
cd mechanism && uv sync
EVAL_SOURCE_DATABASE_URL=postgresql://... uv run python evals/extract_dataset.py
```

`EVAL_SOURCE_DATABASE_URL` is required — the script fails loud if unset. Point
it at a Postgres URL with read access to the conversation history table this
eval draws from.

The runner, scorer, and comparison tool are not yet implemented; this is the
extraction half of the harness.

[#13]: https://github.com/Pondsiders/Alpha/issues/13
