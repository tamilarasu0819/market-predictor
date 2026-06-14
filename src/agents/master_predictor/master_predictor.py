import pandas as pd
import yfinance as yf
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import warnings
import os

warnings.filterwarnings('ignore')

MACRO_TICKERS = ['^NSEI', '^GSPC', '^IXIC', 'USO', '^VIX', '^INDIAVIX']

INDUSTRY_TO_INDEX_MAP = {
    'Technology': '^CNXIT',          
    'Energy': '^CNXENERGY',          
    'Consumer Cyclical': '^CNXCONSUM',
    'Consumer Defensive': '^CNXFMCG', 
    'Financial Services': '^NSEBANK', 
    'Healthcare': '^CNXPHARMA',      
    'Industrials': '^CNXINFRA',      
    'Basic Materials': '^CNXMETAL',   
    'Utilities': '^CNXPSE',          
    'Real Estate': '^CNXREALTY'      
}

CUSTOM_OVERRIDE = {
    'IREDA.NS': '^CNXPSE',    
    'SUZLON.NS': '^CNXENERGY' 
}

def get_dynamic_sector_ticker(ticker):
    if ticker in CUSTOM_OVERRIDE:
        mapped_index = CUSTOM_OVERRIDE[ticker]
        print(f" -> [SYSTEM] Override Engaged: Routed '{ticker}' directly to {mapped_index}")
        return mapped_index
        
    try:
        stock_info = yf.Ticker(ticker).info
        stock_sector = stock_info.get('sector', 'Unknown')
        mapped_index = INDUSTRY_TO_INDEX_MAP.get(stock_sector, '^NSEI')
        print(f" -> [SYSTEM] API detected sector: '{stock_sector}'. Routed to {mapped_index}")
        return mapped_index
    except Exception:
        print(" -> [SYSTEM] Could not fetch sector API. Defaulting to ^NSEI.")
        return '^NSEI'

def fetch_technical_data(ticker, period="5y"):
    df = yf.download(ticker, period=period, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    # STATIONARITY FIX: Convert raw price to a clean ratio
    df['Price_to_SMA'] = df['Close'] / df['SMA_20']
    
    df['Stock_SMA_14'] = df['Close'].rolling(window=14).mean() 
    
    df['Std_Dev_20'] = df['Close'].rolling(window=20).std()
    df['BB_Stretch'] = (df['Close'] - df['SMA_20']) / df['Std_Dev_20']
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI_14'] = 100 - (100 / (1 + rs))
    
    df['Volume_SMA_20'] = df['Volume'].rolling(window=20).mean()
    df['Volume_SMA_20'] = df['Volume_SMA_20'].replace(0, np.nan).fillna(1)
    df['Volume_Anomaly'] = df['Volume'] / df['Volume_SMA_20']
    
    # Calculate BOTH targets so the engine can choose dynamically later
    df['Target_1D'] = (df['Close'].shift(-1) > df['Close']).astype(int)
    df['Target_5D'] = (df['Close'].shift(-5) > df['Close']).astype(int)
    
    df.reset_index(inplace=True)
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    
    return df.dropna()

def fetch_macro_technicals(period="5y"):
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

def fetch_sector_data(sector_ticker, period="5y"):
    try:
        s_df = yf.download(sector_ticker, period=period, progress=False)
        if isinstance(s_df.columns, pd.MultiIndex):
            s_df.columns = s_df.columns.get_level_values(0)
        s_df['Sector_SMA_14'] = s_df['Close'].rolling(window=14).mean()
        s_df.reset_index(inplace=True)
        s_df['Date'] = pd.to_datetime(s_df['Date']).dt.date
        return s_df[['Date', 'Sector_SMA_14']].dropna()
    except Exception:
        return pd.DataFrame(columns=['Date', 'Sector_SMA_14'])

def load_sentiment_data(filepath='sentiment_history.csv'):
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

    sector_ticker = get_dynamic_sector_ticker(ticker)
    tech_df = fetch_technical_data(ticker)
    macro_tech_df = fetch_macro_technicals()
    sector_df = fetch_sector_data(sector_ticker)
    
    sent_df = load_sentiment_data()
    ticker_sent = sent_df[sent_df['Ticker'] == ticker][['Date', 'Weighted_Score', 'Polarized_Score']]
    macro_sent_df = prep_macro_sentiment(sent_df)
    
    merged_df = pd.merge(tech_df, ticker_sent, on='Date', how='left')
    merged_df = pd.merge(merged_df, macro_tech_df, on='Date', how='left')
    merged_df = pd.merge(merged_df, macro_sent_df, on='Date', how='left')
    merged_df = pd.merge(merged_df, sector_df, on='Date', how='left')
    
    merged_df['Sector_SMA_14'] = merged_df['Sector_SMA_14'].replace(0, np.nan)
    merged_df['RS_Ratio'] = merged_df['Stock_SMA_14'] / merged_df['Sector_SMA_14']
    merged_df['RS_Ratio_Signal'] = merged_df['RS_Ratio'].rolling(window=20).mean()
    merged_df['Sector_Gravity'] = merged_df['RS_Ratio'] - merged_df['RS_Ratio_Signal']
    
    merged_df['Weighted_Score'] = merged_df['Weighted_Score'].fillna(0.0)
    merged_df['Polarized_Score'] = merged_df['Polarized_Score'].fillna(0.0)
    merged_df['Sector_Gravity'] = merged_df['Sector_Gravity'].fillna(0.0)
    merged_df['BB_Stretch'] = merged_df['BB_Stretch'].fillna(0.0)
    
    for m in MACRO_TICKERS:
        col_name = f'{m}_Sentiment'
        if col_name in merged_df.columns:
            merged_df[col_name] = merged_df[col_name].fillna(0.0)
            
    merged_df = merged_df.ffill().fillna(0.0)
    
    row_count = len(merged_df)
    recent_turnover = (merged_df['Close'].iloc[-20:] * merged_df['Volume'].iloc[-20:]).mean()
    LIQUIDITY_THRESHOLD = 6_000_000_000  
    
    # Replaced SMA_20 with Price_to_SMA
    all_possible_features = ['Price_to_SMA', 'RSI_14', 'Weighted_Score', 'Polarized_Score', 'Sector_Gravity', 'BB_Stretch', 'Volume_Anomaly']
    for m in MACRO_TICKERS:
        all_possible_features.append(f'{m}_Return')
        all_possible_features.append(f'{m}_Sentiment')
        
    features = [f for f in all_possible_features if f in merged_df.columns]
    
    # DYNAMIC HORIZON ROUTING
    if row_count < 500:
        print(f" -> [SYSTEM] IPO Detected ({row_count} rows). Engaging 1-Day Momentum Horizon.")
        rf_max_depth = 3
        rf_min_samples_leaf = 5
        target_col = 'Target_1D'
        shift_val = 1
    elif recent_turnover < LIQUIDITY_THRESHOLD:
        print(f" -> [SYSTEM] Mid-Cap Detected. Engaging 5-Day Swing Horizon & Deep Trees.")
        rf_max_depth = 7
        rf_min_samples_leaf = 2
        target_col = 'Target_5D'
        shift_val = 5
    else:
        print(f" -> [SYSTEM] Mega-Cap Detected. Engaging 5-Day Swing Horizon & Shallow Trees.")
        rf_max_depth = 4
        rf_min_samples_leaf = 5
        target_col = 'Target_5D'
        shift_val = 5
        
    X_full = merged_df[features]
    y = merged_df[target_col]
    
    # We must slice the historical data based on the dynamic shift_val so we don't leak future data
    X_historical_full = X_full.iloc[:-shift_val]
    y_historical = y.iloc[:-shift_val]
    X_latest_full = X_full.iloc[[-1]]
    
    # PASS 1: Auto-Pruner
    audit_model = RandomForestClassifier(n_estimators=100, max_depth=rf_max_depth, random_state=42)
    audit_model.fit(X_historical_full, y_historical)
    
    feature_importances = pd.Series(audit_model.feature_importances_, index=features).sort_values(ascending=False)
    top_features = feature_importances.head(6).index.tolist()
    top_3_display = feature_importances.head(3).index.tolist()
    
    print(f" -> [SYSTEM] Auto-Pruner kept Top 6 signals. Top 3: {', '.join(top_3_display)}")
    
    # PASS 2: Final Prediction
    X_pruned = merged_df[top_features]
    X_latest_pruned = X_pruned.iloc[[-1]] 
    X_historical_pruned = X_pruned.iloc[:-shift_val]
    
    split_index = int(len(X_historical_pruned) * 0.80)
    X_train, X_test = X_historical_pruned.iloc[:split_index], X_historical_pruned.iloc[split_index:]
    y_train, y_test = y_historical.iloc[:split_index], y_historical.iloc[split_index:]
    
    final_model = RandomForestClassifier(
        n_estimators=150,        
        max_depth=rf_max_depth,             
        min_samples_split=10,    
        min_samples_leaf=rf_min_samples_leaf,      
        random_state=42
    )
    final_model.fit(X_train, y_train)
    
    test_predictions = final_model.predict(X_test)
    real_accuracy = accuracy_score(y_test, test_predictions) * 100
    
    final_model.fit(X_historical_pruned, y_historical)
    live_prediction = final_model.predict(X_latest_pruned)[0]
    direction = "UP 🔼" if live_prediction == 1 else "DOWN 🔽"
    
    print(f" -> Accuracy: {real_accuracy:.2f}% | Prediction: {direction}")

if __name__ == "__main__":
    print("===========================================")
    print("     FULL MACRO-AWARE PREDICTION ENGINE    ")
    print("===========================================")
    
    test_universe = ["TCS.NS", "RELIANCE.NS", "ETERNAL.NS", "SUZLON.NS", "IREDA.NS"]
    for t in test_universe:
        run_master_prediction(t)
    print("\n===========================================")