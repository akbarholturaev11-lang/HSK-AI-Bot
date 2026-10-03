import unittest

from app.services.hsk30_feature_service import (
    DEFAULT_HSK30_LIVE_LEVELS,
    Hsk30FeatureService,
)


class Hsk30FeatureServiceDefaultsTests(unittest.TestCase):
    def test_runtime_ready_n1_to_n3_are_live_by_default(self):
        self.assertEqual(
            ("nhsk1", "nhsk2", "nhsk3"),
            DEFAULT_HSK30_LIVE_LEVELS,
        )
        self.assertEqual(
            ("nhsk1", "nhsk2", "nhsk3"),
            Hsk30FeatureService._normalize_live_levels(None),
        )

    def test_unavailable_n4_is_still_filtered(self):
        self.assertEqual(
            ("nhsk1", "nhsk2", "nhsk3"),
            Hsk30FeatureService._normalize_live_levels(
                "nhsk1,nhsk2,nhsk3,nhsk4"
            ),
        )


if __name__ == "__main__":
    unittest.main()
