"""Ensure the shared loading/ready geometry assertion fails on actual shifts."""
import unittest

from tests.pwa_layout_geometry import assert_reserved_layout


class PwaSkeletonGeometryContractTests(unittest.TestCase):
    @staticmethod
    def slots():
        return {
            "heading": {"x": 16, "y": 130, "width": 210, "height": 40},
            "podium": {"x": 16, "y": 205, "width": 358, "height": 195},
            "member-count": {"x": 16, "y": 412, "width": 358, "height": 30},
            "top-five": {"x": 16, "y": 462, "width": 358, "height": 32},
            "row-1": {"x": 16, "y": 516, "width": 358, "height": 52},
            "bottom-nav": {"x": 18, "y": 740, "width": 354, "height": 80},
        }

    def test_layout_matching_all_slots_passes(self):
        assert_reserved_layout(self.slots(), self.slots())

    def test_missing_skeleton_slot_fails(self):
        before = self.slots()
        del before["podium"]
        with self.assertRaisesRegex(AssertionError, "Unmatched visual slots"):
            assert_reserved_layout(before, self.slots())

    def test_large_blank_area_or_vertical_shift_fails(self):
        before = self.slots()
        # The Rating screenshot's one-card loading state would omit the
        # podium/rows; a displaced podium is also a regression.
        before["podium"]["y"] = 290
        with self.assertRaisesRegex(AssertionError, "podium.y"):
            assert_reserved_layout(before, self.slots())

    def test_short_skeleton_card_instead_of_real_podium_fails(self):
        before = self.slots()
        before["podium"]["height"] = 70
        with self.assertRaisesRegex(AssertionError, "podium.height"):
            assert_reserved_layout(before, self.slots())

    def test_small_rounding_differences_are_allowed(self):
        before = self.slots()
        before["heading"]["y"] += 3
        before["podium"]["height"] -= 9
        assert_reserved_layout(before, self.slots())


if __name__ == "__main__":
    unittest.main()
