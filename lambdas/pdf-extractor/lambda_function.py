"""
PDF text-extraction Lambda.

Triggered by S3 "object create" events on raw-docs/. Extracts the real
embedded text layer from PDFs using pdfplumber (not an image-based/vision
parser) and writes clean .txt files to extracted-docs/, mirroring the
source folder structure. Non-PDF text files (.txt, .md, .csv) are passed
through unchanged so every document type ends up in one reliable,
plain-text corpus for the Knowledge Base to ingest.

Why pdfplumber instead of Bedrock's built-in "Foundation model as a parser":
that parser renders each PDF page as an image and has a vision model
transcribe it, which silently dropped a nested bullet list on a real
production-shaped document in this project. pdfplumber reads the PDF's
actual text objects directly, which is both more reliable and cheaper for
born-digital (non-scanned) documents like these.

Deployment notes:
- Runtime: Python 3.13 (must match the Lambda layer's compiled ABI exactly)
- Memory: 1024 MB (128 MB caused 196s runs that silently returned 0 chars)
- Timeout: 5 min
- Layer: pdfplumber built via `docker run ... public.ecr.aws/sam/build-python3.13`
  or `pip install pdfplumber --platform manylinux_2_28_x86_64 --only-binary=:all:
  --python-version 3.13 --implementation cp`
- VPC: not required for this function (only talks to S3)
"""

import boto3
import pdfplumber
import io
import urllib.parse

s3 = boto3.client("s3")

TEXT_PASSTHROUGH_EXTENSIONS = (".txt", ".md", ".csv")

def lambda_handler(event, context):
    for record in event["Records"]:
        bucket = record["s3"]["bucket"]["name"]
        key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])
        key_lower = key.lower()

        new_key = key.replace("raw-docs/", "extracted-docs/", 1)

        if key_lower.endswith(".pdf"):
            print(f"Extracting PDF: s3://{bucket}/{key}")
            response = s3.get_object(Bucket=bucket, Key=key)
            pdf_bytes = response["Body"].read()

            extracted_text = []
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                print(f"Number of pages detected: {len(pdf.pages)}")
                for page_num, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text()
                    text_len = len(text) if text else 0
                    print(f"Page {page_num}: extracted {text_len} characters")
                    if text:
                        extracted_text.append(f"--- Page {page_num} ---\n{text}")

            full_text = "\n\n".join(extracted_text)
            print(f"TOTAL extracted length: {len(full_text)} characters")

            new_key = new_key.rsplit(".", 1)[0] + ".txt"

            s3.put_object(
                Bucket=bucket, Key=new_key,
                Body=full_text.encode("utf-8"), ContentType="text/plain"
            )
            print(f"Wrote {len(full_text)} characters to: s3://{bucket}/{new_key}")

        elif key_lower.endswith(TEXT_PASSTHROUGH_EXTENSIONS):
            print(f"Passing through text file: s3://{bucket}/{key}")
            s3.copy_object(
                Bucket=bucket,
                CopySource={"Bucket": bucket, "Key": key},
                Key=new_key
            )

        else:
            print(f"Skipping unsupported file type: {key}")

    return {"status": "done"}