import sys
from rag import answer_question


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python query.py '<your question>'")
        sys.exit(1)
    
    question = " ".join(sys.argv[1:])
    answer = answer_question(question)
    print(answer)