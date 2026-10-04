# Enterprise RAG Pipeline on AWS Bedrock

A secure, internal-document-grounded chatbot built on Amazon Bedrock and
Bedrock AgentCore, with an automated ingestion pipeline, private
networking, content guardrails, and a measured evaluation baseline.


## What this demonstrates

This project was built with a deliberate focus on things that separate a
working demo from a defensible, production-minded system:

- **A real evaluation baseline, not a demo that "seems to work."** The
  system went from ~10-15% to 90% factual accuracy on a 20-question golden
  dataset, across three distinct, root-caused failures (see `eval/README.md`).
- **Automated LLM evaluators are not accuracy checks**, and this project
  proves it: the built-in evaluators scored the system perfectly (1.00
  Faithfulness/Correctness/Relevance) even at the 10-15% accuracy stage,
  because an honest "not found" answer is technically faithful and
  relevant. The real accuracy number only comes from manually grading
  against a ground-truth answer key -- a distinction worth understanding
  before trusting any LLM-as-judge metric at face value.
- **A parsing failure that doesn't throw an error is still a failure.**
  Bedrock's vision-model PDF parser silently dropped specific policy
  figures from a document with no warning, failed sync, or error log --
  the only way to find it was testing retrieval against a verbatim quote
  from the source PDF. Fixed by switching to direct text-layer extraction
  with `pdfplumber`, after first ruling out several other causes.
- **Private networking end-to-end.** All Bedrock traffic from the query
  Lambda runs through VPC Interface Endpoints, not the public internet.
- **An automated, trigger-based MLOps pipeline**, not a one-time manual
  setup: new documents are extracted, converted, and re-indexed
  automatically on upload.
- **Evaluation results computed from source data, not hand-entered.** The
  eval-logger Lambda pulls real metrics from CloudWatch's
  `GetMetricData` API and writes them to Postgres -- no number in the
  database was typed in by a person.

## Architecture

See [`docs/architecture.md`](docs/architecture.md) for the full diagram
and the reasoning behind each non-obvious design choice (two Aurora
clusters, a custom PDF-extraction stage, a plain Lambda instead of the
Gateway's built-in Knowledge Base connector, Interface Endpoints instead
of a NAT Gateway).

**Stack:** Amazon Bedrock (Claude), Bedrock Knowledge Bases, Bedrock
AgentCore (Harness + Gateway), Aurora PostgreSQL Serverless v2 (pgvector
+ a separate application database), AWS Lambda, Amazon S3, VPC Interface
Endpoints, Bedrock Guardrails, CloudWatch (Evaluations, Transaction
Search, dashboards, alarms).

## Repository structure

```
lambdas/
  pdf-extractor/     Extracts real text from PDFs (pdfplumber), passes .txt/.md/.csv through
  kb-sync-trigger/    Triggers Knowledge Base re-ingestion on new/updated documents
  kb-query/           MCP tool target: retrieval + generation against the Knowledge Base
  eval-logger/         Pulls real eval metrics from CloudWatch, logs them to Postgres
db/
  schema.sql           Chat history, feedback, and eval_runs tables
eval/
  golden_dataset.csv   20 hand-written Q&A pairs used as the evaluation set
docs/
  architecture.md       Full diagram and design-decision rationale
```

## Results

| Metric | Value |
|---|---|
| Manually-verified accuracy (final baseline) | 18/20 (90%) |
| Automated Faithfulness / Relevance / Correctness | 1.00 / 1.00 / 1.00 |
| Automated Helpfulness | 0.83 |
| Automated Refusal rate | 0.00 |

See `eval/README.md` for the full three-stage progression (10-15% → 55%
→ 90%) and what each stage's failure actually was.

## What's not built yet

- An authenticated end-user client (today the only way to query the
  system is the AWS console's Harness playground) -- the natural next
  phase, calling the Harness's `invoke_agent_runtime` API from a simple
  web front end behind Cognito.
- A quality gate on the automated re-ingestion pipeline (new documents
  sync unconditionally; a production version would eval-check post-sync
  before treating a new index as authoritative).

Both are documented in `docs/architecture.md` under "Known limitations."

## Observability

A CloudWatch dashboard (Lambda health, Bedrock usage, Aurora capacity,
live evaluation scores) and two alarms (query errors, a cluster stuck
running instead of scaling to zero). See
[`docs/observability.md`](docs/observability.md) — it also covers a real
cost incident this setup was built in response to.

## Cost notes

Built and run within a small personal AWS budget. The main lesson:
**VPC Interface Endpoints bill continuously per-AZ, unlike nearly
everything else in this stack** (Lambda, Bedrock, and Aurora Serverless
v2 with `min capacity: 0` all scale to near-zero when idle). Endpoints
were deliberately scoped to 1-2 Availability Zones rather than the
default of all available AZs once this was identified as the largest
cost driver.
