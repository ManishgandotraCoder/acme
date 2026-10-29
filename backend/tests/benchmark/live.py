"""Ask the predefined questions to a real model through the running API.

Checks that the model selects the expected operation and entities (the numbers themselves are
verified deterministically by test_salary_questions.py). Not part of the test suite: it needs
a running app and a model, and costs money for cloud providers.

    make dev-api                      # in another terminal
    make benchmark-llm                # default provider
    make benchmark-llm provider=anthropic
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

from tests.benchmark.questions import QUESTIONS, BenchmarkQuestion

ENTITIES = ("countries", "departments", "job_titles")


def ask(url: str, question: str, provider: str | None) -> dict:
    body = {"question": question} | ({"provider": provider} if provider else {})
    request = urllib.request.Request(
        f"{url}/api/ask", json.dumps(body).encode(), {"content-type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)


def mismatches(expected: BenchmarkQuestion, result: dict) -> list[str]:
    intent = result["intent"]
    problems = []
    if result["kind"] != "answer":
        problems.append(f"kind={result['kind']}")
    if intent["metric"] != expected.metric:
        problems.append(f"metric={intent['metric']} (expected {expected.metric})")
    for key in ENTITIES:
        if sorted(intent[key]) != sorted(getattr(expected, key)):
            problems.append(f"{key}={intent[key]} (expected {getattr(expected, key)})")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--provider", default=None, help="ollama | anthropic | openai")
    args = parser.parse_args()

    passed, provider = 0, None
    for q in QUESTIONS:
        started = time.perf_counter()
        try:
            result = ask(args.url, q.question, args.provider)
        except urllib.error.HTTPError as error:
            print(f"FAIL  {q.question}\n      HTTP {error.code}: {error.read().decode()[:200]}")
            continue
        provider = result.get("provider")
        problems = mismatches(q, result)
        passed += not problems
        status = "ok  " if not problems else "FAIL"
        print(f"{status}  [{time.perf_counter() - started:4.1f}s] {q.category}: {q.question}")
        for problem in problems:
            print(f"      {problem}")

    print(f"\n{passed}/{len(QUESTIONS)} questions understood (provider: {provider})")
    return 0 if passed == len(QUESTIONS) else 1


if __name__ == "__main__":
    sys.exit(main())
