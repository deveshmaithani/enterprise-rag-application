"""
Knowledge Base query Lambda.

Registered as an MCP tool target on an AgentCore Gateway, which is attached
to the AgentCore Harness (the actual chat agent). The Harness calls this
tool whenever it needs to answer a question from the internal document
corpus; this function performs retrieval + generation against the Bedrock
Knowledge Base and returns the answer with source citations.

numberOfResults is explicitly set to 15 (Bedrock's default is 5). This was
raised during evaluation debugging: a verbatim-text test confirmed a known
document's content was present in the vector store but not being retrieved
at the default top-5 cutoff. Raising it meaningfully improved recall but
also increased per-query latency -- the Lambda timeout had to be raised
from 3s (AWS default) to 60s to accommodate the larger context Claude has
to read through per answer.
"""

import json
import os
import boto3

bedrock_agent_runtime = boto3.client("bedrock-agent-runtime")

KB_ID = os.environ["KNOWLEDGE_BASE_ID"]
MODEL_ARN = os.environ["MODEL_ARN"]

def lambda_handler(event, context):
    question = event.get("question", "")
    if not question:
        return {"error": "No question provided"}

    response = bedrock_agent_runtime.retrieve_and_generate(
        input={"text": question},
        retrieveAndGenerateConfiguration={
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {
            "knowledgeBaseId": KB_ID,
            "modelArn": MODEL_ARN,
            "retrievalConfiguration": {
                "vectorSearchConfiguration": {
                "numberOfResults": 15
                }
            }
        }
        }
    )

    answer = response["output"]["text"]
    citations = []
    for citation in response.get("citations", []):
        for ref in citation.get("retrievedReferences", []):
            uri = ref.get("location", {}).get("s3Location", {}).get("uri", "")
            if uri:
                citations.append(uri)

    return {
        "answer": answer,
        "sources": citations
    }