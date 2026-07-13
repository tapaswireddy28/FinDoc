"""Command line interface for the Financial RAG app.

Usage:
    python cli.py ingest "../data/AnnualReport.pdf"
    python cli.py ask "What were the main risks in 2024?"
    python cli.py summarize
"""
import argparse
from rag import RAGPipeline
def main():
    parser = argparse.ArgumentParser(description="Financial RAG (fully local)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="parse, chunk, embed and store a document")
    p_ingest.add_argument("path", help="path to a .pdf or .txt file")

    p_ask = sub.add_parser("ask", help="ask a question about the ingested document")
    p_ask.add_argument("question", help="your question (in quotes)")

    sub.add_parser("summarize", help="summarize the ingested document")

    args = parser.parse_args()
    rag = RAGPipeline()

    if args.command == "ingest":
        n = rag.ingest(args.path)
        print(f"\nDone. Ingested {n} chunks. Now try:\n"
              f'  python cli.py ask "your question here"')

    elif args.command == "ask":
        result = rag.ask(args.question)
        print("\n" + "=" * 70)
        print("ANSWER:\n" + result["answer"])
        pages = ", ".join(str(p) for p in result["pages"])
        print(f"\nSources: page(s) {pages}")
        print("=" * 70)

    elif args.command == "summarize":
        print("\n" + "=" * 70)
        print("SUMMARY:\n" + rag.summarize())
        print("=" * 70)


if __name__ == "__main__":
    main()
