import pandas as pd
import yfinance as yf
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import warnings
import os

warnings.filterwarnings('ignore')

MACRO_TICKERS = ['^NSEI', '^GSPC', '^IXIC', 'USO']

def fetch_technical_data(ticker, period="2y"):
    """Fetches target stock data and calculates local technical and microstructure indicators."""
    df = yf.download(ticker, period=period, progress=False)
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI_14'] = 100 - (100 / (1 + rs))
    
    # Microstructure: Volume Dynamics calculated but conditionally used later
    df['Volume_SMA_20'] = df['Volume'].rolling(window=20).mean()
    df['Volume_SMA_20'] = df['Volume_SMA_20'].replace(0, np.nan).fillna(1)
    df['Volume_Anomaly'] = df['Volume'] / df['Volume_SMA_20']
    
    df['Target'] = (df['Close'].shift(-1) > df['Close']).astype(int)
    
    df.reset_index(inplace=True)
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    
    return df.dropna()

def fetch_macro_technicals(period="2y"):
    """Fetches historical daily returns for global macro indices."""
    df_macro = pd.DataFrame()
    
    for ticker in MACRO_TICKERS:
        try:
            m_df = yf.download(ticker, period=period, progress=False)
            if isinstance(m_df.columns, pd.MultiIndex):
                m_df.columns = m_df.columns.get_level_values(0)
                
            m_df[f'{ticker}_Return'] = m_df['Close'].pct_change()
            m_df.reset_index(inplace=True)
            m_df['Date'] = pd.to_datetime(m_df['Date']).dt.date
            
            m_df = m_df[['Date', f'{ticker}_Return']]
            
            if df_macro.empty:
                df_macro = m_df
            else:
                df_macro = pd.merge(df_macro, m_df, on='Date', how='outer')
        except Exception:
            pass
            
    return df_macro

def load_sentiment_data(filepath='sentiment_history.csv'):
    """Loads the cloud-scraped sentiment data from valid paths."""
    if not os.path.exists(filepath) and os.path.exists('../../sentiment_history.csv'):
        filepath = '../../sentiment_history.csv'
    elif not os.path.exists(filepath) and os.path.exists('../sentiment_history.csv'):
        filepath = '../sentiment_history.csv'

    try:
        sent_df = pd.read_csv(filepath)
        sent_df['Date'] = pd.to_datetime(sent_df['Timestamp']).dt.date
        sent_df = sent_df.groupby(['Date', 'Ticker']).last().reset_index()
        return sent_df[['Date', 'Ticker', 'Weighted_Score', 'Polarized_Score']]
    except FileNotFoundError:
        return pd.DataFrame(columns=['Date', 'Ticker', 'Weighted_Score', 'Polarized_Score'])

def prep_macro_sentiment(sent_df):
    """Isolates sentiment scores for global indices safely."""
    if not sent_df.empty:
        df_macro_sent = pd.DataFrame({'Date': sent_df['Date'].unique()})
    else:
        df_macro_sent = pd.DataFrame(columns=['Date'])
    
    for ticker in MACRO_TICKERS:
        col_name = f'{ticker}_Sentiment'
        m_sent = sent_df[sent_df['Ticker'] == ticker]
        
        if not m_sent.empty:
            m_sent = m_sent[['Date', 'Weighted_Score']].rename(columns={'Weighted_Score': col_name})
            df_macro_sent = pd.merge(df_macro_sent, m_sent, on='Date', how='outer')
        else:
            df_macro_sent[col_name] = np.nan
            
    return df_macro_sent

def run_master_prediction(ticker):
    print(f"\nRunning Engine for: {ticker}...")

    tech_df = fetch_technical_data(ticker)
    macro_tech_df = fetch_macro_technicals()
    
    sent_df = load_sentiment_data()
    ticker_sent = sent_df[sent_df['Ticker'] == ticker][['Date', 'Weighted_Score', 'Polarized_Score']]
    macro_sent_df = prep_macro_sentiment(sent_df)
    
    merged_df = pd.merge(tech_df, ticker_sent, on='Date', how='left')
    merged_df = pd.merge(merged_df, macro_tech_df, on='Date', how='left')
    merged_df = pd.merge(merged_df, macro_sent_df, on='Date', how='left')
    
    merged_df['Weighted_Score'] = merged_df['Weighted_Score'].fillna(0.0)
    merged_df['Polarized_Score'] = merged_df['Polarized_Score'].fillna(0.0)
    
    for m in MACRO_TICKERS:
        col_name = f'{m}_Sentiment'
        if col_name in merged_df.columns:
            merged_df[col_name] = merged_df[col_name].fillna(0.0)
            
    merged_df = merged_df.ffill().fillna(0.0)
    
    # ---------------------------------------------------------
    # THE LIQUIDITY GATE: DYNAMIC FEATURE ROUTING
    # ---------------------------------------------------------
    recent_turnover = (merged_df['Close'].iloc[-20:] * merged_df['Volume'].iloc[-20:]).mean()
    LIQUIDITY_THRESHOLD = 6_000_000_000  # Tuned 6 Billion Turnover threshold
    
    features = ['SMA_20', 'RSI_14', 'Weighted_Score', 'Polarized_Score']
    
    if recent_turnover < LIQUIDITY_THRESHOLD:
        print(f" -> [SYSTEM] High-Beta/Mid-Cap Detected (Turnover: {recent_turnover:,.0f}). Engaging Volume Tracking.")
        features.append('Volume_Anomaly')
    else:
        print(f" -> [SYSTEM] Mega-Cap Liquidity Detected (Turnover: {recent_turnover:,.0f}). Filtering volume noise.")
    
    for m in MACRO_TICKERS:
        features.append(f'{m}_Return')
        features.append(f'{m}_Sentiment')
    # ---------------------------------------------------------
        
    X = merged_df[features]
    y = merged_df['Target']
    
    X_latest = X.iloc[[-1]] 
    X_historical = X.iloc[:-1]
    y_historical = y.iloc[:-1]
    
    split_index = int(len(X_historical) * 0.80)
    X_train, X_test = X_historical.iloc[:split_index], X_historical.iloc[split_index:]
    y_train, y_test = y_historical.iloc[:split_index], y_historical.iloc[split_index:]
    
    model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
    model.fit(X_train, y_train)
    
    test_predictions = model.predict(X_test)
    real_accuracy = accuracy_score(y_test, test_predictions) * 100
    
    model.fit(X_historical, y_historical)
    live_prediction = model.predict(X_latest)[0]
    direction = "UP 🔼" if live_prediction == 1 else "DOWN 🔽"
    
    print(f" -> Accuracy: {real_accuracy:.2f}% | Prediction: {direction}")

if __name__ == "__main__":
    print("===========================================")
    print("     DYNAMIC HYBRID ROUTING ENGINE TEST    ")
    print("===========================================")
    
    test_universe = ["TCS.NS", "RELIANCE.NS", "ETERNAL.NS", "SUZLON.NS", "IREDA.NS"]
    for t in test_universe:
        run_master_prediction(t)
    print("\n===========================================")