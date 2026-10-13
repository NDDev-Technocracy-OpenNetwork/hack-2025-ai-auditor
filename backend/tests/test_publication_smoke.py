import unittest

from pydantic import ValidationError

from app.main import app
from app.schemas.prompts import MetricScore, PromptInput


class PublicationSmoke(unittest.TestCase):
    def test_api_schema_contains_health(self):
        self.assertIn('/healthz', app.openapi()['paths'])

    def test_prompt_validation_retains_content(self):
        self.assertEqual(PromptInput(content='Example prompt').content, 'Example prompt')

    def test_metric_scores_reject_out_of_range(self):
        with self.assertRaises(ValidationError):
            MetricScore(score=11, rationale='Invalid score')
