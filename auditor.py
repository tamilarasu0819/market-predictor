import sys
import yfinance as yf

def audit_universe():
    print("===========================================")
    print("    Running Health Check on Universe...    ")
    print("===========================================")
    
    with open('universe.txt', 'r') as f:
        tickers = [line.strip() for line in f if line.strip()]
        
    broken_tickers = []
    data = yf.download(tickers, period="1d", progress=False)
    
    for ticker in tickers:
        if data['Close'][ticker].isna().all():
            print(f"❌ INVALID TICKER: {ticker} does not exist on Yahoo Finance.")
            broken_tickers.append(ticker)
            
    print("\n===========================================")
    if not broken_tickers:
        print("✅ SUCCESS: All tickers are healthy.")
        print("===========================================")
        sys.exit(0) # 0 means "All Good" to the server
    else:
        print(f"⚠️ FOUND {len(broken_tickers)} BROKEN TICKERS.")
        print("===========================================")
        sys.exit(1) # 1 means "Warning/Error" to the server

if __name__ == "__main__":
    audit_universe()