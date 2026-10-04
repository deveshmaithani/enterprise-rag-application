# eval-logger Lambda

Pulls evaluation results directly from CloudWatch (where AgentCore's
batch evaluation feature publishes them as Embedded Metric Format custom
metrics, namespace `Bedrock-AgentCore/Evaluations`) and inserts an
averaged row into the `eval_runs` table. No evaluation numbers are typed
in by hand anywhere in this pipeline.

## Build the pg8000 layer (pure Python, no compiled dependencies)

```bash
mkdir -p python
pip install pg8000 -t python/
zip -r pg8000-layer.zip python
aws lambda publish-layer-version \
  --layer-name pg8000-layer \
  --zip-file fileb://pg8000-layer.zip \
  --compatible-runtimes python3.13
```

pg8000 is pure Python with no C extensions, so unlike pdfplumber it
doesn't need the Docker-based build process -- a plain `pip install`
works regardless of the build machine's architecture.

## Required environment variables
`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`

## Required IAM permissions
- `AWSLambdaVPCAccessExecutionRole` (runs inside the VPC to reach Aurora)
- `CloudWatchReadOnlyAccess` (to call `GetMetricData`)

## Required VPC endpoints
This function calls both Aurora (inside the VPC, via a security-group
rule allowing the Lambda's security group to reach Aurora's own) and the
CloudWatch Monitoring API, which needs its own VPC Interface Endpoint
(`com.amazonaws.<region>.monitoring`) since this VPC has no NAT Gateway
and therefore no general internet route.

## Invocation
```json
{
  "run_id": "<batch-evaluation-run-id>",
  "config_label": "a-short-label-for-this-eval-run",
  "service_name": "<harness-name>.DEFAULT"
}
```

`run_id` and `service_name` must match the exact dimension values
CloudWatch published for the evaluation run -- find them by expanding any
single evaluation-result log event in
`/aws/bedrock-agentcore/evaluations/batch-evaluations/results/default`
and reading the `runId` and `service.name` fields directly, rather than
guessing the format.

## A note on why this exists
The straightforward version of this function would just take the eval
scores as hardcoded input values. That's not how a real pipeline should
work -- scores should be computed from the actual measurement, not
transcribed by a person. This version queries CloudWatch's
`GetMetricData` API directly so the numbers in the database always trace
back to a real, reproducible measurement.
