import unittest

from freelance_bot.models import Opportunity
from freelance_bot.scoring import score_one
from freelance_bot.sources import extract_budget


class ScoringTest(unittest.TestCase):
    def test_scores_skill_and_budget_match(self):
        item = Opportunity(
            source="test",
            title="Need React developer for Shopify automation",
            url="https://example.com/job",
            description="Fixed price budget $500. Need this week.",
            budget="$500",
        )

        score, reasons = score_one(
            item,
            skills=["react", "shopify", "automation"],
            blocked_keywords=["unpaid"],
            must_include_any=[],
            title_include_any=[],
        )

        self.assertGreaterEqual(score, 70)
        self.assertTrue(any("skill match" in reason for reason in reasons))

    def test_blocks_bad_keywords(self):
        item = Opportunity(
            source="test",
            title="Build app for exposure",
            url="https://example.com/job",
            description="No budget but great exposure.",
        )

        score, reasons = score_one(
            item,
            skills=["app"],
            blocked_keywords=["exposure"],
            must_include_any=[],
            title_include_any=[],
        )

        self.assertEqual(score, 0)
        self.assertEqual(reasons, ["blocked keyword: exposure"])

    def test_blocks_risky_job_posts(self):
        item = Opportunity(
            source="test",
            title="Remote React developer",
            url="https://example.com/job",
            description="Pay a registration fee before the client interview.",
        )

        score, reasons = score_one(
            item,
            skills=["react"],
            blocked_keywords=[],
            must_include_any=[],
            title_include_any=[],
            scam_keywords=["registration fee"],
        )

        self.assertEqual(score, 0)
        self.assertEqual(reasons, ["risk keyword: registration fee"])

    def test_rewards_trusted_sources(self):
        item = Opportunity(
            source="test",
            title="Need Python automation developer",
            url="https://example.com/job",
            description="Ongoing contract work.",
            reliability=90,
        )

        score, reasons = score_one(
            item,
            skills=["python", "automation"],
            blocked_keywords=[],
            must_include_any=[],
            title_include_any=[],
        )

        self.assertGreaterEqual(score, 50)
        self.assertIn("trusted source", reasons)

    def test_budget_extraction_requires_pay_context(self):
        self.assertEqual(extract_budget("Fixed price budget $500. Need this week."), "$500")
        self.assertEqual(extract_budget("We have paid over $11M to developers."), "")

    def test_blocks_old_posts_when_recency_is_configured(self):
        item = Opportunity(
            source="test",
            title="Need Python developer",
            url="https://example.com/job",
            description="Ongoing contract.",
            published_at="2020-01-01T00:00:00+00:00",
        )

        score, reasons = score_one(
            item,
            skills=["python"],
            blocked_keywords=[],
            must_include_any=[],
            title_include_any=[],
            max_age_days=45,
        )

        self.assertEqual(score, 0)
        self.assertEqual(reasons, ["older than 45 days"])


if __name__ == "__main__":
    unittest.main()
