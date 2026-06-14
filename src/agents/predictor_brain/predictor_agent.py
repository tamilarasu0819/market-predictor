import sys
import os
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

# Add the src directory to Python's import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Import Phase 1 and Phase 2 functions
from agents.data_fetcher.fetch_stock import fetch_stock_data
from agents.indicator_brain.indicator_agent import calculate_indicators

def run_baseline_prediction(ticker, period='2y'):
    """Fetches data, calculates indicators, and evaluates baseline accuracy for any given ticker."""
    print("===========================================")
    print(f"      AI Predictor Agent: {ticker}         ")
    print("===========================================")
    
    # 1. Fetch data dynamically
    print(f"\nFetching {period} of data for {ticker}...")
    df = fetch_stock_data(ticker, period=period)
    
    if df is not None and not df.empty:
        # 2. Pass data through calculate_indicators
        print("Calculating SMA and RSI indicators...")
        df = calculate_indicators(df)
        
        if not df.empty:
            # 3. Create 'Target' column and drop NaNs
            print("Creating Target variable for prediction...")
            df['Tomorrow_Close'] = df['Close'].shift(-1)
            df.dropna(inplace=True)
            
            df['Target'] = np.where(df['Tomorrow_Close'] > df['Close'], 1, 0)
            
            # 4. Use 'SMA' and 'RSI' as features (X) and 'Target' as label (y)
            print("Extracting features and labels...")
            X = df[['SMA', 'RSI']]
            y = df['Target']
            
            # 5. Split data (80% train, 20% test, shuffle=False)
            print("Splitting data into 80% train and 20% test sets...")
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
            
            # 6. Train RandomForestClassifier
            print("Training the RandomForestClassifier...")
            clf = RandomForestClassifier(random_state=42)
            clf.fit(X_train, y_train)
            
            # 7. Predict and print Accuracy
            print("Making predictions on the test set...")
            predictions = clf.predict(X_test)
            
            acc = accuracy_score(y_test, predictions)
            print(f"\nModel Evaluation complete!")
            print(f"Final Accuracy Score: {acc * 100:.2f}%")
            print("===========================================")
            return acc
        else:
            print("\nNot enough data points after calculating indicators.")
            return None
    else:
        print(f"\nCould not fetch valid data for {ticker}.")
        return None

if __name__ == "__main__":
    # Check if a ticker was passed via the command line
    if len(sys.argv) > 1:
        target_ticker = sys.argv[1]
    else:
        # Fallback to Reliance if no argument is provided
        print("No ticker provided in terminal. Defaulting to RELIANCE.NS")
        target_ticker = 'RELIANCE.NS'
        
    run_baseline_prediction(target_ticker)