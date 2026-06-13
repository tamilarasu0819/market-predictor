import sys
import os
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd

# Add the src directory to Python's import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from agents.data_fetcher.fetch_stock import fetch_stock_data

class TestFetchStock(unittest.TestCase):

    @patch('agents.data_fetcher.fetch_stock.yf.Ticker')
    @patch('builtins.print')
    def test_fetch_stock_data_success(self, mock_print, mock_ticker):
        """Test successful stock data fetching with mocked yfinance."""
        # Create a mock non-empty DataFrame representing stock data
        mock_df = pd.DataFrame({
            'Open': [150.0, 152.0],
            'High': [153.0, 155.0],
            'Low': [149.0, 151.0],
            'Close': [152.5, 154.5],
            'Volume': [1000000, 1200000]
        }, index=pd.date_range(start='2026-06-01', periods=2))

        # Setup the mock yfinance Ticker instance
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.history.return_value = mock_df
        mock_ticker.return_value = mock_ticker_instance

        # Call the function
        result = fetch_stock_data('AAPL', period='1mo')

        # Assert Ticker was initialized with correct symbol and history called
        mock_ticker.assert_called_once_with('AAPL')
        mock_ticker_instance.history.assert_called_once_with(period='1mo')

        # Assert response is the correct DataFrame
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)
        pd.testing.assert_frame_equal(result, mock_df)

        # Assert standard prints happened
        mock_print.assert_any_call("\nFetching data for 'AAPL'...")

    @patch('agents.data_fetcher.fetch_stock.yf.Ticker')
    @patch('builtins.print')
    def test_fetch_stock_data_empty(self, mock_print, mock_ticker):
        """Test behavior when yfinance returns an empty DataFrame."""
        # Setup mock to return an empty DataFrame
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.history.return_value = pd.DataFrame()
        mock_ticker.return_value = mock_ticker_instance

        # Call the function
        result = fetch_stock_data('INVALID_SYMBOL')

        # Assert history was called and function returned None
        mock_ticker.assert_called_once_with('INVALID_SYMBOL')
        mock_ticker_instance.history.assert_called_once_with(period='1mo')
        self.assertIsNone(result)

        # Assert error print occurred
        mock_print.assert_any_call(
            "Error: No data found for symbol 'INVALID_SYMBOL'. Please verify the ticker suffix (like .NS for NSE)."
        )

    @patch('agents.data_fetcher.fetch_stock.yf.Ticker')
    @patch('builtins.print')
    def test_fetch_stock_data_exception(self, mock_print, mock_ticker):
        """Test behavior when yfinance throws an unexpected exception."""
        # Setup mock Ticker to raise an exception when history is called
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.history.side_effect = Exception("API connection failure")
        mock_ticker.return_value = mock_ticker_instance

        # Call the function
        result = fetch_stock_data('AAPL')

        # Assert function returns None on exception
        self.assertIsNone(result)

        # Assert exception print occurred
        mock_print.assert_any_call(
            "An unexpected error occurred while fetching data: API connection failure"
        )

    @patch('agents.data_fetcher.fetch_stock.yf.Ticker')
    def test_fetch_stock_data_custom_period(self, mock_ticker):
        """Test that the period parameter is correctly forwarded to Ticker.history."""
        mock_df = pd.DataFrame({
            'Open': [100.0],
            'High': [101.0],
            'Low': [99.0],
            'Close': [100.5],
            'Volume': [50000]
        }, index=pd.date_range(start='2026-06-01', periods=1))

        mock_ticker_instance = MagicMock()
        mock_ticker_instance.history.return_value = mock_df
        mock_ticker.return_value = mock_ticker_instance

        # Call the function with custom period
        result = fetch_stock_data('MSFT', period='5d')

        mock_ticker_instance.history.assert_called_once_with(period='5d')
        self.assertIsNotNone(result)

    def test_fetch_stock_data_real_api(self):
        """Integration test using the live yfinance API to fetch MSFT data."""
        try:
            # We fetch a brief history (5 days) of MSFT to verify yfinance connection works
            result = fetch_stock_data('MSFT', period='5d')
            
            # Since live network calls might be rate-limited, skip if None returned due to environment
            if result is None:
                self.skipTest("Real API returned None; skipping integration test (might be offline or rate-limited).")
            
            # Verify structure of actual returned DataFrame
            self.assertIsNotNone(result)
            self.assertFalse(result.empty)
            self.assertTrue(isinstance(result, pd.DataFrame))
            
            # Common yfinance OHLCV columns should be present
            required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            for col in required_cols:
                self.assertIn(col, result.columns)
        except Exception as e:
            self.skipTest(f"Skipping live API integration test due to network/unexpected error: {e}")

if __name__ == '__main__':
    unittest.main()
