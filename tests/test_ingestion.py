import os
import sys
import tempfile
import unittest


# Allow tests to import modules from src/projectpulse
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

PROJECTPULSE_SRC = os.path.join(
    PROJECT_ROOT,
    "src",
    "projectpulse",
)

sys.path.insert(0, PROJECTPULSE_SRC)


from storage import load_documents, save_documents


DATA_FILE = os.path.join(
    PROJECT_ROOT,
    "data",
    "github_documents.json",
)


class TestProjectPulseIngestion(unittest.TestCase):

    def test_github_documents_exist(self):
        """
        Verify that the ingestion pipeline produced documents.
        """

        documents = load_documents(DATA_FILE)

        self.assertGreater(
            len(documents),
            0,
            "No GitHub documents were stored.",
        )


    def test_document_schema(self):
        """
        Verify every stored document follows the
        ProjectPulse standard schema.
        """

        documents = load_documents(DATA_FILE)

        required_fields = {
            "id",
            "source",
            "type",
            "title",
            "content",
            "author",
            "created_at",
            "updated_at",
            "url",
            "metadata",
        }

        valid_types = {
            "issue",
            "pull_request",
            "commit",
        }

        for document in documents:

            self.assertTrue(
                required_fields.issubset(document.keys())
            )

            self.assertEqual(
                document["source"],
                "github",
            )

            self.assertIn(
                document["type"],
                valid_types,
            )

            self.assertTrue(document["id"])
            self.assertTrue(document["title"])
            self.assertTrue(document["url"])


    def test_document_ids_are_unique(self):
        """
        Verify documents cannot collide during
        future indexing.
        """

        documents = load_documents(DATA_FILE)

        document_ids = [
            document["id"]
            for document in documents
        ]

        self.assertEqual(
            len(document_ids),
            len(set(document_ids)),
        )


    def test_storage_round_trip(self):
        """
        Verify documents remain unchanged after
        save and load operations.
        """

        sample_documents = [
            {
                "id": "test_document_1",
                "source": "github",
                "type": "commit",
                "title": "Test commit",
                "content": "Test content",
                "author": "test_user",
                "created_at": "2026-08-09T00:00:00Z",
                "updated_at": "2026-08-09T00:00:00Z",
                "url": "https://example.com",
                "metadata": {
                    "sha": "abc123"
                },
            }
        ]

        with tempfile.TemporaryDirectory() as temp_dir:

            test_file = os.path.join(
                temp_dir,
                "documents.json",
            )

            save_documents(
                sample_documents,
                test_file,
            )

            loaded_documents = load_documents(
                test_file,
            )

            self.assertEqual(
                sample_documents,
                loaded_documents,
            )


if __name__ == "__main__":
    unittest.main()