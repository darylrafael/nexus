import sys
from orchestrator.gemini import run
from memory.obsidian import write_note, read_recent_notes
from delivery.telegram import send_report
from datetime import datetime


def main():
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = input("Enter your query: ").strip()

    if not query:
        print("No query provided.")
        return

    print(f"\nNexus processing: {query}")

    print("  [memory] loading past context...")
    context = read_recent_notes(days=7)

    print("-" * 50)
    result = run(query, context=context)
    print(result)
    print("-" * 50)

    title = f"{datetime.now().strftime('%Y-%m-%d-%H%M')} - {query[:50]}"
    saved = write_note(title, f"# {query}\n\n{result}")
    if saved:
        print(f"  [memory] saved to Obsidian: {title}")

    send_report(f"Nexus Report\nQuery: {query}\n\n{result}")


if __name__ == "__main__":
    main()
