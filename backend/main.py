from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import sys
import os
import requests
import yfinance as yf

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from master_predictor import run_master_prediction

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/search")
def search_tickers(query: str = Query(..., description="Search query for ticker symbol")):
    try:
        if not query or len(query) < 1:
            return []
            
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}&quotesCount=6&newsCount=0"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        quotes = data.get("quotes", [])
        
        results = []
        for q in quotes:
            # Check if it's an equity or similar instrument that has a symbol
            if "symbol" in q:
                results.append({
                    "symbol": q.get("symbol"),
                    "shortname": q.get("shortname", q.get("longname", q.get("symbol")))
                })
                
        return results
    except Exception as e:
        print(f"[WARN] Search error: {e}")
        return []

@app.get("/predict")
def get_stock_prediction(
    ticker: str = Query(..., description="Stock ticker symbol (e.g., TCS.NS)"),
    period: str = Query("1mo", description="Historical data period (1wk, 1mo, 3mo, 1y)")
):
    try:
        ticker = ticker.upper().strip()
        result = run_master_prediction(ticker)
        if not result:
            return {"error": f"Failed to generate prediction data for {ticker}"}

        # --- Inject real-time OHLCV via yfinance ---
        historical_prices = []
        current_price = None
        open_price    = None
        high_price    = None
        low_price     = None
        volume        = None
        try:
            stock = yf.Ticker(ticker)
            hist  = stock.history(period=period)
            if not hist.empty:
                last = hist.iloc[-1]
                current_price = round(float(last["Close"]),  2)
                open_price    = round(float(last["Open"]),   2)
                high_price    = round(float(last["High"]),   2)
                low_price     = round(float(last["Low"]),    2)
                volume        = int(last["Volume"])
                
                for date, row in hist.iterrows():
                    historical_prices.append({
                        "time": date.strftime("%Y-%m-%d"),
                        "open": round(float(row["Open"]), 2),
                        "high": round(float(row["High"]), 2),
                        "low": round(float(row["Low"]), 2),
                        "close": round(float(row["Close"]), 2)
                    })
        except Exception as price_err:
            print(f"[WARN] Could not fetch live OHLCV for {ticker}: {price_err}")

        result["current_price"] = current_price
        result["open"]          = open_price
        result["high"]          = high_price
        result["low"]           = low_price
        result["volume"]        = volume
        result["historical_prices"] = historical_prices

        return result
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
