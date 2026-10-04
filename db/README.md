# db/

## schema.sql
Run once via a Lambda inside the VPC (RDS has no public access). See
`lambdas/eval-logger/README.md` for the pg8000-layer build steps, which
this also depends on.

## Why two Aurora clusters
The Knowledge Base's vector store (Aurora pgvector) is created and managed
internally by Bedrock when the Knowledge Base is set up -- its schema is
not meant to be touched directly. This schema lives on a **separate**
Aurora Serverless v2 cluster (`enterprise-rag-metadata-db`), created
independently, for the application's own audit/eval data. Keeping them
separate avoids mixing Bedrock-managed internals with application tables,
and lets each scale and be backed up independently.

Both clusters scale to 0 ACU when idle (`Minimum capacity: 0`, `Pause
after inactivity: 5 min`), which matters for cost -- see the root
README's "Cost notes" section.
