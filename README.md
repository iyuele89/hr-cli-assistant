# Qi4M Practice Assistant

A Python command-line assistant that answers questions about fictional
company policies and employee leave balances. It combines document
retrieval, LLM tool calling, and JSONL input/output.

## Setup

Requires Python 3.10 or newer and an OpenAI API key with available credit.

Run these commands in Windows PowerShell from the project folder:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install openai python-dotenv
```

Create a `.env` file in the project folder:

```dotenv
OPENAI_API_KEY=your_api_key_here
```

Add these rules to the project’s `.gitignore`:

```gitignore
.venv/
.env
__pycache__/
```

## Input

Place the company policy text files in `docs/`.

Create `practice_queries.jsonl` with one JSON object per line.
Each object must contain `id` and `question`:

```jsonl
{"id":"q1","question":"How many days of annual leave do employees receive?"}
{"id":"q2","question":"How many leave days does employee E001 have left?"}
{"id":"q3","question":"How much is the annual performance bonus?"}
{"id":"q4","question":"How many leave days does employee E999 have left?"}
```

## Execution

Run from the project folder so the application can locate `.env`,
`docs/`, and the input file:

```powershell
.\.venv\Scripts\python.exe practice_app.py
```

The application writes `practice_answers.jsonl`. Each output line
contains the original `id`, the `question`, and the final `answer`.
Each run overwrites the output file.

API requests consume credit.

## How It Works

Each question starts a fresh conversation with `gpt-6-luna`.
The model has access to two Python functions:

- `search_documents(query)` retrieves the top two company documents.
- `get_leave_balance(employee_id)` returns a fictional employee’s
  remaining leave days or an employee-not-found error.

The first model request requires a tool call. Subsequent requests allow
the model to request another tool or produce its final answer.
Python executes requested functions and sends their results back to
the model. Each question permits a maximum of five model requests.

The model is instructed to cite source filenames for policy answers
and report when the available information does not answer a question.

## Retrieval Method and Limitations

The retriever lowercases the query and each document, splits the text
on whitespace, and converts the resulting words into sets. It scores
each document by the number of distinct words shared with the query,
then returns the two highest-scoring documents with their filenames,
scores, and contents.

This simple method is easy to inspect but does not account for synonyms,
word importance, or punctuation. Common words can produce irrelevant
matches. Documents with zero overlap can still be returned, and equal
scores have no semantic preference.

The model must assess whether the retrieved text supports an answer.
Prompt instructions and source citations do not guarantee correctness.

## Manual Checks

Run the four sample questions and inspect the answers:

| ID | Expected behavior |
|---|---|
| q1 | Answers 25 days and cites `leave.txt` |
| q2 | Uses the leave-balance tool and answers 12 days |
| q3 | Reports that bonus information is unavailable |
| q4 | Reports that employee E999 was not found |

These are expected results to verify when running the application.