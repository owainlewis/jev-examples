# Jev examples

Basic Python examples for TypeSafe AI's Jev model. Each script contains sample data, calls Jev, and prints a suggested result.

## Run an example

You need Python 3.10 or newer and an API key from the [TypeSafe console](https://console.typesafe.ai).

From the repository root, run these commands on macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Set your key in the same terminal:

```bash
read -r -s TYPESAFE_API_KEY
export TYPESAFE_API_KEY
```

After the first command, paste your key and press Enter. The terminal hides what you type. The scripts read the key from the environment; they do not load `.env` files.

Run any script directly:

```bash
python src/01-classify-emails.py
```

Edit the sample data inside a script to try your own input. Each run sends that data to the hosted API. The search example makes three requests; the others make one each.

## Examples

| Script | What it shows |
| --- | --- |
| [01-classify-emails.py](src/01-classify-emails.py) | Choose billing, support, sales, or another inbox |
| [02-classify-github-issues.py](src/02-classify-github-issues.py) | Suggest low, medium, high, or unknown change risk |
| [03-prioritize-support.py](src/03-prioritize-support.py) | Score whether a customer's work is blocked |
| [04-classify-documents.py](src/04-classify-documents.py) | Sort document text by type |
| [05-tag-feedback.py](src/05-tag-feedback.py) | Apply several tags to one feedback message |
| [06-filter-search-results.py](src/06-filter-search-results.py) | Select passages that help answer a question |
| [07-find-duplicate-issues.py](src/07-find-duplicate-issues.py) | Suggest duplicate reports for review |

The scripts print suggestions. They do not move emails, update GitHub, or merge code. Thresholds are examples to test on your own data. API errors stop the script instead of producing a default decision.

## Guides

- [Start here: classify emails and GitHub issues](docs/tutorial.md)
- [More use cases: support, documents, feedback, search, and duplicates](docs/use-cases.md)
