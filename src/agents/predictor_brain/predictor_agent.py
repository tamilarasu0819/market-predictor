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

if __name__ == "__main__":
    print("===========================================")
    print("      AI Predictor Agent Initialized       ")
    print("===========================================")

    ticker = 'RELIANCE.NS'
    period = '2y'
    
    # 1. Fetch 2 years of data
    print(f"\nFetching {period} of data for {ticker}...")
    df = fetch_stock_data(ticker, period=period)
    
    if df is not None and not df.empty:
        # 2. Pass data through calculate_indicators
        print("Calculating SMA and RSI indicators...")
        df = calculate_indicators(df)
        
        if not df.empty:
            # 3. Create 'Target' column and drop NaNs
            print("Creating Target variable for prediction...")
            # We use shift(-1) to look ahead to tomorrow's close
            df['Tomorrow_Close'] = df['Close'].shift(-1)
            
            # Drop rows with NaN values (specifically the last row which won't have a 'tomorrow')
            df.dropna(inplace=True)
            
            # Target is 1 if tomorrow's Close > today's Close, else 0
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
        else:
            print("\nNot enough data points after calculating indicators.")
    else:
        print(f"\nCould not fetch valid data for {ticker}.")
