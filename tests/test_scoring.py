import unittest

from freelance_bot.models import Opportunity
from freelance_bot.notify import safe_send
from freelance_bot.scoring import score_one
from freelance_bot.sources import extract_budget, extract_location


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

    def test_blocks_jobs_outside_target_location(self):
        item = Opportunity(
            source="test",
            title="Product Manager",
            url="https://example.com/job",
            description="Full-time role for a B2B SaaS product.",
            location="United States",
        )

        score, reasons = score_one(
            item,
            skills=["product manager", "saas"],
            blocked_keywords=[],
            must_include_any=[],
            title_include_any=["product manager"],
            location_include_any=["india", "apac", "anywhere"],
        )

        self.assertEqual(score, 0)
        self.assertEqual(reasons, ["location is outside target regions"])

    def test_rewards_india_product_management_match(self):
        item = Opportunity(
            source="test",
            title="Senior Product Manager",
            url="https://example.com/job",
            description="Own product strategy, roadmap, user research, and SaaS analytics.",
            location="Remote - India",
            reliability=90,
        )

        score, reasons = score_one(
            item,
            skills=["product strategy", "roadmap", "user research", "saas"],
            blocked_keywords=[],
            must_include_any=[],
            title_include_any=["product manager"],
            location_include_any=["india", "apac", "anywhere"],
        )

        self.assertGreaterEqual(score, 80)
        self.assertTrue(any("location match" in reason for reason in reasons))

    def test_location_matching_does_not_match_inside_words(self):
        item = Opportunity(
            source="test",
            title="Product Manager",
            url="https://example.com/job",
            description="Own a specialist product workflow.",
            location="Berlin",
            reliability=90,
        )

        score, reasons = score_one(
            item,
            skills=["product manager"],
            blocked_keywords=[],
            must_include_any=[],
            title_include_any=["product manager"],
            location_include_any=["ist"],
        )

        self.assertEqual(score, 0)
        self.assertEqual(reasons, ["location is outside target regions"])

    def test_extracts_rss_headquarters_location(self):
        self.assertEqual(
            extract_location("Headquarters: Remote - India URL: https://example.com About us"),
            "Remote - India",
        )

    def test_remote_without_specific_location_can_use_description_region(self):
        item = Opportunity(
            source="test",
            title="Product Manager",
            url="https://example.com/job",
            description="This role can be done from anywhere in the world.",
            location="Remote",
            reliability=90,
        )

        score, reasons = score_one(
            item,
            skills=["product manager"],
            blocked_keywords=[],
            must_include_any=[],
            title_include_any=["product manager"],
            location_include_any=["anywhere in the world"],
        )

        self.assertGreater(score, 0)
        self.assertTrue(any("location match" in reason for reason in reasons))

    def test_notification_errors_do_not_crash_run(self):
        def broken_sender(_payload):
            raise OSError("network failed")

        self.assertEqual(safe_send("telegram", broken_sender, []), "telegram failed: network failed")


if __name__ == "__main__":
    unittest.main()
