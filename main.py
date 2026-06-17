import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from chat import ask


if __name__ == "__main__":
    while True:
        question = input("\nAsk a question (or 'quit' to exit): ").strip()
        if question.lower() in ("quit", "exit", "q"):
            break
        if not question:
            continue
        print("\n" + ask(question))
