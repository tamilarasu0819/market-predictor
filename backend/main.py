from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import sys
import os
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

@app.get("/predict")
def get_stock_prediction(ticker: str = Query(..., description="Stock ticker symbol (e.g., TCS.NS)")):
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
            hist  = stock.history(period="1mo")
            if not hist.empty:
                last = hist.iloc[-1]
                current_price = round(float(last["Close"]),  2)
                open_price    = round(float(last["Open"]),   2)
                high_price    = round(float(last["High"]),   2)
                low_price     = round(float(last["Low"]),    2)
                volume        = int(last["Volume"])
                
                for date, row in hist.iterrows():
                    historical_prices.append({
                        "date": date.strftime("%b %d"),
                        "price": round(float(row["Close"]), 2)
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
