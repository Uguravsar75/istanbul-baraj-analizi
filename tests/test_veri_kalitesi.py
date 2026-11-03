#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Istanbul Dams Data Quality & Schema Integrity Unit Tests
========================================================
Validates time-series continuity, primary-key uniqueness, value bounds,
and schema consistency across raw and derived datasets.
"""

from pathlib import Path
import unittest
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent


class TestDataQuality(unittest.TestCase):
    """Automated unit tests for raw and processed hydrological datasets."""

    @classmethod
    def setUpClass(cls):
        cls.df_occ = pd.read_csv(BASE_DIR / "dam_occupancy.csv")
        cls.df_xl = pd.read_excel(
            BASE_DIR / "istanbul-barajlarnda-ya-ve-gunluk-tuketim-verileri.xlsx",
            sheet_name="Sayfa1",
        )
        cls.df_merged = pd.read_csv(BASE_DIR / "data" / "istanbul_baraj_birlesik_veri.csv")
        cls.df_unpivot = pd.read_csv(BASE_DIR / "data" / "istanbul_baraj_yagis_unpivot.csv")

    def test_occupancy_uniqueness_and_continuity(self):
        """dam_occupancy.csv must contain zero duplicate dates and zero missing days."""
        self.assertEqual(self.df_occ.isnull().sum().sum(), 0, "Dataset must not contain NaN values.")
        self.assertEqual(
            self.df_occ["DATE"].duplicated().sum(),
            0,
            "DATE column must not contain duplicate dates (Primary Key violation).",
        )
        dt = pd.to_datetime(self.df_occ["DATE"])
        expected_days = (dt.max() - dt.min()).days + 1
        self.assertEqual(
            len(self.df_occ),
            expected_days,
            "Time series must be strictly continuous without skipped dates.",
        )

    def test_occupancy_value_bounds(self):
        """Occupancy rate must lie within [0, 100]% and reserved water must be positive."""
        rate = self.df_occ["GENERAL_DAM_OCCUPANCY_RATE"]
        reserve = self.df_occ["GENERAL_DAM_RESERVED_WATER"]
        self.assertTrue(((rate >= 0) & (rate <= 100)).all(), "Occupancy rate must be between 0 and 100.")
        self.assertTrue((reserve > 0).all(), "Reserved water volume must be strictly positive.")

    def test_excel_structure_and_cleanliness(self):
        """Excel dataset must have no Unnamed empty columns or NaN values."""
        unnamed_cols = [c for c in self.df_xl.columns if str(c).startswith("Unnamed")]
        self.assertEqual(len(unnamed_cols), 0, f"Unexpected empty columns found: {unnamed_cols}")
        self.assertEqual(self.df_xl.isnull().sum().sum(), 0, "Excel dataset must not contain NaN values.")
        self.assertEqual(len(self.df_xl), 4797, "Excel row count must equal 4,797 days.")

    def test_merged_and_unpivoted_consistency(self):
        """Derived CSV tables must match expected dimensions and non-negative constraints."""
        self.assertEqual(len(self.df_merged), 4797)
        self.assertEqual(
            len(self.df_unpivot),
            len(self.df_merged) * 10,
            "Unpivoted table must equal 10 dams x 4,797 days = 47,970 rows.",
        )
        self.assertEqual(self.df_unpivot["Baraj_Adi"].nunique(), 10, "Must contain exactly 10 unique dams.")
        self.assertTrue((self.df_unpivot["Yagis_mm"] >= 0).all(), "Precipitation cannot be negative.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
