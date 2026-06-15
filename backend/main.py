from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from master_predictor import run_master_prediction

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
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
        return result
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
