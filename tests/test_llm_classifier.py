import unittest
from unittest.mock import patch, MagicMock
from intent.llm_intent_classifier import LLMIntentClassifier
from intent.intent_classifier import Intent

class TestLLMIntentClassifier(unittest.TestCase):
    def setUp(self):
        self.classifier = LLMIntentClassifier()

    @patch('intent.llm_intent_classifier.requests.post')
    def test_classify_n8n_trigger(self, mock_post):
        # Mocking the Ollama response for a complex workflow trigger
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "response": '{"intent": "TRIGGER_N8N", "slots": {"workflow": "send_slack", "parameters": {"recipient": "Alice", "message": "Good morning"}}}'
        }
        mock_post.return_value = mock_response

        text = "Message Alice on Slack saying Good morning"
        intent = self.classifier.classify(text)

        self.assertIsNotNone(intent)
        self.assertEqual(intent.name, "TRIGGER_N8N")
        self.assertEqual(intent.slots["workflow"], "send_slack")
        self.assertEqual(intent.slots["parameters"]["recipient"], "Alice")
        self.assertEqual(intent.slots["parameters"]["message"], "Good morning")

    @patch('intent.llm_intent_classifier.requests.post')
    def test_classify_chat(self, mock_post):
        # Mocking the Ollama response for a chat intent
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "response": '{"intent": "CHAT", "slots": {"response": "I am doing well, thank you!"}}'
        }
        mock_post.return_value = mock_response

        text = "How are you?"
        intent = self.classifier.classify(text)

        self.assertIsNotNone(intent)
        self.assertEqual(intent.name, "CHAT")
        self.assertEqual(intent.slots["response"], "I am doing well, thank you!")

    @patch('intent.llm_intent_classifier.requests.post')
    def test_classify_failure(self, mock_post):
        # Mocking a failure (e.g., connection error or bad JSON)
        mock_post.side_effect = Exception("Connection refused")

        text = "Some command"
        intent = self.classifier.classify(text)

        self.assertIsNone(intent)

if __name__ == '__main__':
    unittest.main()
