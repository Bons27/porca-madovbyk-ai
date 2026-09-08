import unittest

from src.chat_engine import _extract_output_text


class TestChatEngine(unittest.TestCase):
    def test_extract_current_interactions_schema(self):
        payload = {
            "id": "int_123",
            "steps": [
                {
                    "type": "model_output",
                    "content": [
                        {"type": "text", "text": "Prima parte."},
                        {"type": "text", "text": "Seconda parte."},
                    ],
                }
            ],
        }
        self.assertEqual(
            _extract_output_text(payload),
            "Prima parte.\nSeconda parte.",
        )

    def test_extract_compatibility_outputs_schema(self):
        payload = {
            "outputs": [
                {"type": "text", "text": "Risposta compatibile."},
            ]
        }
        self.assertEqual(
            _extract_output_text(payload),
            "Risposta compatibile.",
        )


if __name__ == "__main__":
    unittest.main()
