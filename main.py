import json
from pathlib import Path
from typing import cast
from dotenv import load_dotenv
from openai import OpenAI
from openai.types.responses import ResponseInputItemParam, ResponseInputParam, ToolParam

load_dotenv(".env")
client = OpenAI()


# 1. Define the Python functions
def get_leave_balance(employee_id):
    balances = {"E001": 12, "E002": 7}

    if employee_id not in balances:
        return {"error": "Employee not found"}

    return {
        "employee_id": employee_id,
        "remaining_days": balances[employee_id],
    }
def search_documents(query):
    matches = []
    query_tokens = set(query.lower().split())

    for path in Path("docs").glob("*.txt"):
        text = path.read_text(encoding="utf-8")
        text_tokens = set(text.lower().split())
        score = len(query_tokens & text_tokens)
        matches.append((score, path.name, text))

    matches.sort(key=lambda match: match[0], reverse=True)
    top_ranked_docs = matches[:2]

    return [
        {
            "score": score,
            "source": filename,
            "content": text,
        }
        for score, filename, text in top_ranked_docs
    ]

# print(get_leave_balance("E001"))  # Expected balance: 12
# print(get_leave_balance("E999"))  # Expected: Employee not found

# for document in search_documents("annual bonus"):
#     print(document["source"], document["score"], document["content"])  

# 2. Describe the function to the model.
tools: list[ToolParam] = [
    {
        "type": "function",
        "name": "get_leave_balance",
        "description": "Look up an employee's remaining leave days.",
        "parameters": {
            "type": "object",
            "properties": {
                "employee_id": {
                    "type": "string",
                    "description": "Employee ID, such as E001.",
                }
            },
            "required": ["employee_id"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "search_documents",
        "description": "Search for documents relevant to a query.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query.",
                }
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        "strict": True,
    }
]

instructions = """
Answer questions using information returned by the tools.

Use search_documents for company policy questions.
Use get_leave_balance for an employee's remaining leave balance.

Before answering, check whether the tool results contain the
specific information needed to answer the question.

If the documents contain the answer, answer and cite the filename.
If they do not, say:
"The provided documents do not contain this information."

If an employee is not found, report that.
Do not guess missing facts.
"""

with open("practice_queries.jsonl", encoding="utf-8") as queries_file:
    with open("practice_answers.jsonl", "w", encoding="utf-8") as answers_file:
        for line in queries_file:
            record = json.loads(line)

            messages: ResponseInputParam = [
                {"role": "user", "content": record["question"]}
            ]

            response = None
            for request_number in range(1, 6):
                response = client.responses.create(
                    model="gpt-6-luna",
                    instructions=instructions,
                    input=messages,
                    tools=tools,
                    tool_choice="required" if request_number == 1 else "auto",
                    parallel_tool_calls=False,
                )

                calls = [
                    item for item in response.output
                    if item.type == "function_call"
                ]

                if not calls:
                    if not response.output_text:
                        raise ValueError(f"No answer for question {record['id']}")
                    break

                if request_number == 5:
                    raise RuntimeError(
                        f"No final answer for question {record['id']} "
                        "after five model requests"
                    )

                messages.extend(
                    cast(
                        ResponseInputItemParam,
                        item.model_dump(
                            mode="json", by_alias=True, exclude_none=True
                        ),
                    )
                    for item in response.output
                )

                for call in calls:
                    arguments = json.loads(call.arguments)

                    if call.name == "search_documents":
                        result = search_documents(arguments["query"])
                    elif call.name == "get_leave_balance":
                        result = get_leave_balance(arguments["employee_id"])
                    else:
                        raise ValueError(f"Unknown tool: {call.name}")

                    messages.append({
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": json.dumps(result, ensure_ascii=False),
                    })

            if response is None:
                raise RuntimeError("No model request was made")
            answer = {
                "id": record["id"],
                "question": record["question"],
                "answer": response.output_text,
            }
            answers_file.write(json.dumps(answer, ensure_ascii=False) + "\n")



