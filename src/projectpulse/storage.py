import json
import os

from normalizer import collect_normalized_documents


DATA_DIR = "data"
OUTPUT_FILE = os.path.join(DATA_DIR, "github_documents.json")


def save_documents(documents, output_file=OUTPUT_FILE):
    """
    Save normalized ProjectPulse documents to JSON.
    """

    os.makedirs(DATA_DIR, exist_ok=True)

    with open(
        output_file,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            documents,
            file,
            indent=2,
            ensure_ascii=False,
        )

    return output_file


def load_documents(input_file=OUTPUT_FILE):
    """
    Load previously stored ProjectPulse documents.
    """

    if not os.path.exists(input_file):
        return []

    with open(
        input_file,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


if __name__ == "__main__":
    print("Collecting GitHub activity...")

    documents = collect_normalized_documents()

    output_file = save_documents(documents)

    saved_documents = load_documents(output_file)

    print(f"Documents collected: {len(documents)}")
    print(f"Documents saved: {len(saved_documents)}")
    print(f"Saved to: {output_file}")

    if len(documents) == len(saved_documents):
        print("\nStorage verification successful.")
    else:
        print("\nStorage verification failed.")