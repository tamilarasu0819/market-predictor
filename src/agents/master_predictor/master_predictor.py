import pandas as pd
import yfinance as yf
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import warnings
import os
warnings.filterwarnings('ignore')

def fetch_technical_data(ticker, period="2y"):
    """Fetches stock data and calculates technical indicators."""
    print(f"Fetching technical data for {ticker}...")
    df = yf.download(ticker, period=period, progress=False)
    
    # Flatten MultiIndex columns if yfinance returns them
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # Calculate SMA and RSI
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    
    # Simple RSI calculation
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI_14'] = 100 - (100 / (1 + rs))
    
    # Target: 1 if tomorrow's close is higher than today's, else 0
    df['Target'] = (df['Close'].shift(-1) > df['Close']).astype(int)
    
    # Clean up index to match Date format
    df.reset_index(inplace=True)
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    
    return df.dropna()

def load_sentiment_data(filepath='sentiment_history.csv'):
    """Loads and cleans the cloud-scraped sentiment data."""
    print("Loading sentiment data...")
    
    # Handle paths if running from different directories
    if not os.path.exists(filepath) and os.path.exists('../../sentiment_history.csv'):
        filepath = '../../sentiment_history.csv'
    elif not os.path.exists(filepath) and os.path.exists('../sentiment_history.csv'):
        filepath = '../sentiment_history.csv'

    try:
        sent_df = pd.read_csv(filepath)
        # Convert Timestamp to standard Date format to match yfinance
        sent_df['Date'] = pd.to_datetime(sent_df['Timestamp']).dt.date
        
        # If there are multiple scrapes in one day, keep only the latest one
        sent_df = sent_df.groupby(['Date', 'Ticker']).last().reset_index()
        return sent_df[['Date', 'Ticker', 'Weighted_Score', 'Polarized_Score']]
    except FileNotFoundError:
        print(f"Warning: {filepath} not found! Creating an empty DataFrame.")
        return pd.DataFrame(columns=['Date', 'Ticker', 'Weighted_Score', 'Polarized_Score'])

def run_master_prediction(ticker):
    print("===========================================")
    print("      MASTER PREDICTOR INITIALIZING        ")
    print("===========================================\n")

    # 1. Get Data
    tech_df = fetch_technical_data(ticker)
    sent_df = load_sentiment_data()
    
    # Filter sentiment for just our target ticker
    ticker_sent = sent_df[sent_df['Ticker'] == ticker]
    
    # 2. The Merge
    print(f"Merging Technicals and Sentiment for {ticker}...")
    merged_df = pd.merge(tech_df, ticker_sent, on='Date', how='left')
    
    # Fill historical missing sentiment with 0.0 (Neutral)
    merged_df['Weighted_Score'] = merged_df['Weighted_Score'].fillna(0.0)
    merged_df['Polarized_Score'] = merged_df['Polarized_Score'].fillna(0.0)
    
    # 3. Prepare for Machine Learning
    # Define our features: Technicals + Sentiment
    features = ['SMA_20', 'RSI_14', 'Weighted_Score', 'Polarized_Score']
    
    X = merged_df[features]
    y = merged_df['Target']
    
    # Save the absolute latest row for tomorrow's real-world prediction
    X_latest = X.iloc[[-1]] 
    
    # Take everything EXCEPT the latest row for our historical validation loop
    X_historical = X.iloc[:-1]
    y_historical = y.iloc[:-1]
    
    # Split historical data into 80% Training and 20% Testing sets
    split_index = int(len(X_historical) * 0.80)
    
    X_train, X_test = X_historical.iloc[:split_index], X_historical.iloc[split_index:]
    y_train, y_test = y_historical.iloc[:split_index], y_historical.iloc[split_index:]
    
    # 4. Train the Model on the Training Set only
    print("Training Random Forest Engine...")
    model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
    model.fit(X_train, y_train)
    
    # 5. Evaluate on Unseen Test Set to get the real accuracy profile
    test_predictions = model.predict(X_test)
    real_accuracy = accuracy_score(y_test, test_predictions) * 100
    
    # Retrain on the full historical block right before making the live production prediction
    model.fit(X_historical, y_historical)
    live_prediction = model.predict(X_latest)[0]
    direction = "UP 🔼" if live_prediction == 1 else "DOWN 🔽"
    
    print("\n===========================================")
    print(f"Real Unseen Testing Accuracy: {real_accuracy:.2f}%")
    print(f"Features used: {features}")
    print(f"Prediction for {ticker} next open: {direction}")
    print("===========================================")

if __name__ == "__main__":
    # Test it on a single stock first
    run_master_prediction("TCS.NS")