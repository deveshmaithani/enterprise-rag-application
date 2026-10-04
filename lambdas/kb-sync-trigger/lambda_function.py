"""
Knowledge Base sync-trigger Lambda.

Triggered by S3 "object create" events on extracted-docs/ (the clean-text
output of the pdf-extractor Lambda, not the raw uploads). Starts a Bedrock
Knowledge Base ingestion job so new/updated documents are automatically
re-embedded into the vector store with no manual "Sync" click required.

IMPORTANT: DATA_SOURCE_ID must be updated any time the Knowledge Base's
data source is recreated (e.g. when changing parsing strategy). This
value is NOT automatically discovered -- if the KB's data source was
ever deleted and recreated, this constant goes stale silently (the
function keeps running without error, it just syncs nothing useful).
"""

import boto3

bedrock_agent = boto3.client("bedrock-agent")

KB_ID = "YFZFHENSGF"  # Bedrock Knowledge Base ID
DATA_SOURCE_ID = "REPLACE_WITH_CURRENT_DATA_SOURCE_ID"


def lambda_handler(event, context):
    response = bedrock_agent.start_ingestion_job(
        knowledgeBaseId=KB_ID,
        dataSourceId=DATA_SOURCE_ID
    )
    print("Started ingestion job:", response["ingestionJob"]["ingestionJobId"])
    return {"status": "sync triggered"}
