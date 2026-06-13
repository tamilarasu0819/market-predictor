import yfinance as yf
import pandas as pd

def fetch_stock_data(ticker_symbol, period="1mo"):
    """
    Fetches historical stock data using yfinance.
    
    Parameters:
    - ticker_symbol (str): The stock ticker (e.g., 'RELIANCE.NS', 'AAPL')
    - period (str): The time period of data to fetch (default is '1mo')
    
    Returns:
    - pd.DataFrame: Dataframe containing OHLCV data, or None if failed
    """
    try:
        print(f"\nFetching data for '{ticker_symbol}'...")
        stock = yf.Ticker(ticker_symbol)
        df = stock.history(period=period)
        
        if df.empty:
            print(f"Error: No data found for symbol '{ticker_symbol}'. Please verify the ticker suffix (like .NS for NSE).")
            return None
            
        return df
    except Exception as e:
        print(f"An unexpected error occurred while fetching data: {e}")
        return None

if __name__ == "__main__":
    print("====================================")
    print("   AI Stock Data Fetcher Initialized ")
    print("====================================")
    
    # Accept dynamic user input from the terminal
    user_ticker = input("Enter a stock ticker symbol (e.g., RELIANCE.NS, TCS.NS, AAPL, TSLA): ").strip().upper()
    
    if user_ticker:
        # Fetch the last 1 month of data for the specified ticker
        data = fetch_stock_data(user_ticker, period="1mo")
        
        if data is not None:
            print(f"\nSuccessfully retrieved data for {user_ticker}!")
            print("--- Most Recent 5 Days of Market Data ---")
            # Display the last 5 rows elegantly
            print(data.tail(5).to_string())
            print("====================================")
    else:
        print("Input cannot be empty. Please restart the script and enter a valid ticker.")