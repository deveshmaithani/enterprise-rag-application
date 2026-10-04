# eval/

## golden_dataset.csv
20 question/answer/source-document triples, hand-written against the
project's 4-document corpus (HR policies, finance/expenses, security
standards, engineering security practices). Covers an easy/medium/hard
mix and deliberately includes a couple of questions the system was known
to get wrong early on, as regression tests.

**Add your own copy of this file here before pushing** -- it's
intentionally not duplicated from the working session into this
scaffold, since it's specific to whichever document corpus you're using.

## How evaluation actually works here
AgentCore's batch evaluation re-scores *already-logged* conversations
pulled from CloudWatch (via Transaction Search, which must be enabled
first) -- it does not take a dataset of questions as direct input, and it
has no access to a ground-truth answer key. The workflow is:

1. Ask every question in `golden_dataset.csv` through the live agent
   (Harness playground, or any client calling the Harness).
2. Create a batch evaluation job, pointed at the agent/endpoint. It
   automatically finds and scores the sessions that were just logged.
3. Built-in evaluators (Correctness, Faithfulness, Response relevance,
   Refusal, Helpfulness) score each turn via an LLM-as-judge, with no
   visibility into `golden_dataset.csv`'s expected answers.
4. Separately, manually compare each generated answer against
   `expected_answer` in the CSV -- this is the only step that produces a
   real factual-accuracy number against ground truth.

### Why both steps matter
The automated evaluators alone are not sufficient: an honest "I couldn't
find that in the knowledge base" response scores perfectly on
Faithfulness, Relevance, and Correctness (it's faithful to what was
retrieved and relevant to the question), even when the real answer
existed in the document corpus and simply wasn't retrieved. Relying on
the automated scores alone would have reported ~100% quality on a system
that was actually failing to answer most questions correctly.

## Results from this project

| Pipeline stage | Manually-verified accuracy | Root cause of failures |
|---|---|---|
| Original (image-based LLM PDF parser) | ~10-15% | Vision-model parser silently dropped a nested bullet list on one document; same failure mode suspected across others |
| After switching to pdfplumber text extraction | 55% (65% w/ partial credit) | Source PDFs had a font encoding that made text visually selectable but not programmatically extractable -- affected every parsing method tried, not just the original one |
| After regenerating source PDFs with standard font encoding | 90% | Remaining 2/20 misses traced to incomplete content carried over during manual PDF regeneration (a copy/paste gap), not a retrieval or parsing defect |

Automated evaluator scores on the final (90%) baseline: Faithfulness
1.00, Response relevance 1.00, Correctness 1.00, Refusal 0.00,
Helpfulness 0.83 (reviewing individual score explanations showed 0.83 is
this evaluator's normal rating for a genuinely good answer, not a defect
signal -- see root README for how to interpret these metrics).
