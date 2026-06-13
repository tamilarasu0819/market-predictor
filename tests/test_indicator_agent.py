import sys
import os
import unittest
import pandas as pd
import numpy as np

# Add the src directory to Python's import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from agents.indicator_brain.indicator_agent import calculate_indicators

class TestIndicatorAgent(unittest.TestCase):

    def test_standard_success(self):
        """Standard Success: A normal 20-day dataframe where it successfully drops NaNs and calculates SMA/RSI."""
        dates = pd.date_range(start='2026-01-01', periods=20)
        # Create a trend to ensure valid RSI calculation
        prices = [100 + i + (i % 3) for i in range(20)]
        df = pd.DataFrame({'Close': prices}, index=dates)
        
        result = calculate_indicators(df, sma_window=14, rsi_window=14)
        
        # 20 days - 14 days of NaNs (1 for diff + 13 for 14-day rolling) = 6 days remaining
        self.assertEqual(len(result), 6)
        self.assertIn('SMA', result.columns)
        self.assertIn('RSI', result.columns)
        self.assertFalse(result.isnull().values.any())

    def test_empty_null_handling(self):
        """Empty/Null Handling: Passing empty dataframes or completely None values."""
        # Test None
        self.assertIsNone(calculate_indicators(None))
        
        # Test empty DataFrame
        empty_df = pd.DataFrame()
        result_empty = calculate_indicators(empty_df)
        self.assertTrue(result_empty.empty)

    def test_deduplication_edge_case(self):
        """The Deduplication Edge Case: A dataframe where the same date appears 3 times in a row."""
        dates = list(pd.date_range(start='2026-01-01', periods=18))
        # Insert duplicate dates to make a total of 20 rows, but only 18 unique
        duplicate_date = dates[4]
        dates.insert(5, duplicate_date)
        dates.insert(5, duplicate_date)
        
        prices = list(range(100, 120))
        df = pd.DataFrame({'Close': prices}, index=pd.DatetimeIndex(dates))
        
        # We start with 20 rows
        self.assertEqual(len(df), 20)
        
        result = calculate_indicators(df, sma_window=14, rsi_window=14)
        
        # Unique dates should be 18.
        # After a 14-day rolling window on 18 days (with diff adding 1 day of NaN), we have 18 - 14 = 4 days left.
        self.assertEqual(len(result), 4)
        # Ensure that no duplicate indices remain in the result
        self.assertFalse(result.index.duplicated().any())

    def test_insufficient_data(self):
        """Insufficient Data: A dataframe with only 5 days of data. Ensure it doesn't crash."""
        dates = pd.date_range(start='2026-01-01', periods=5)
        df = pd.DataFrame({'Close': [100, 101, 102, 101, 100]}, index=dates)
        
        result = calculate_indicators(df, sma_window=14, rsi_window=14)
        
        # Since it needs 14 days, all rows will have NaN for SMA/RSI and will be dropped.
        self.assertTrue(result.empty)

    def test_mathematical_stability_constant_price(self):
        """Mathematical Stability: Constant price leading to 0 gain and 0 loss (0/0 division)."""
        dates = pd.date_range(start='2026-01-01', periods=20)
        df = pd.DataFrame({'Close': [100.0] * 20}, index=dates)
        
        # Shouldn't crash. Since 0/0 gives NaN for pandas, the rows will be dropped.
        result = calculate_indicators(df, sma_window=14, rsi_window=14)
        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue(result.empty)

    def test_mathematical_stability_only_gain(self):
        """Mathematical Stability: Price only goes up (0 loss, division by zero)."""
        dates = pd.date_range(start='2026-01-01', periods=20)
        df = pd.DataFrame({'Close': [100.0 + i for i in range(20)]}, index=dates)
        
        result = calculate_indicators(df, sma_window=14, rsi_window=14)
        
        # Should not crash. RSI should be 100 for all calculated rows.
        self.assertFalse(result.empty)
        self.assertTrue((result['RSI'] == 100.0).all())

    def test_mathematical_stability_only_loss(self):
        """Mathematical Stability: Price only goes down (0 gain)."""
        dates = pd.date_range(start='2026-01-01', periods=20)
        df = pd.DataFrame({'Close': [100.0 - i for i in range(20)]}, index=dates)
        
        result = calculate_indicators(df, sma_window=14, rsi_window=14)
        
        # Should not crash. RSI should be 0 for all calculated rows.
        self.assertFalse(result.empty)
        self.assertTrue((result['RSI'] == 0.0).all())

if __name__ == '__main__':
    unittest.main()
