import time
import sys
from src.agents.sentiment_brain.sentiment_agent import analyze_sentiment

def run_daily_scrape():
    print("===========================================", flush=True)
    print("    Starting Daily Universe News Scrape    ", flush=True)
    print("===========================================", flush=True)
    
    with open('universe.txt', 'r') as f:
        tickers = [line.strip() for line in f if line.strip()]
        
    for i, ticker in enumerate(tickers):
        print(f"\n[{i + 1}/{len(tickers)}] Processing {ticker}...", flush=True)
        analyze_sentiment(ticker)
        
        # 3-second sleep to prevent Yahoo from IP banning us
        time.sleep(3)
        
    print("\n===========================================", flush=True)
    print(" Daily Scrape Complete! Data appended to CSV.", flush=True)
    print("===========================================", flush=True)

if __name__ == "__main__":
    run_daily_scrape()