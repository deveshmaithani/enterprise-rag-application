# pdf-extractor Lambda

Converts raw PDFs into clean, reliably-parseable `.txt` files before they
reach the Bedrock Knowledge Base.

## Build the Lambda layer (pdfplumber)

CloudShell, using AWS's official Lambda build image to avoid any
architecture/ABI mismatch between the build machine and the actual Lambda
runtime:

```bash
mkdir -p python
docker run --rm -v "$PWD/python":/var/task public.ecr.aws/sam/build-python3.13:latest \
  pip install pdfplumber -t /var/task/
zip -r pdfplumber-layer.zip python
aws lambda publish-layer-version \
  --layer-name pdfplumber-layer \
  --zip-file fileb://pdfplumber-layer.zip \
  --compatible-runtimes python3.13
```

Attach the resulting layer ARN to this function. **The Lambda's own runtime
must be set to Python 3.13** (not 3.14 or any other version) — a compiled
C-extension layer built for one Python minor version will not import under
a different one, even if both are "compatible" per the console label.

## Trigger

S3 event notification on the bucket, prefix `raw-docs/`, "All object create
events", destination = this function.

## Known limitation

Some PDFs generated via a browser's "Print to PDF" can use a font encoding
that makes the text visually selectable but not programmatically
extractable by any text-extraction library (pdfplumber, pypdf, or
Bedrock's own parsers all fail identically on these). If extraction
silently returns 0 characters per page despite the source PDF being a
real, non-scanned document, regenerate the source PDF through a different
export path (e.g., copy the content into a word processor and export from
there) rather than debugging the extraction code further.
