import os
import csv
import sys
import torch
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timedelta, timezone
from transformers import pipeline

# --- LOAD MODEL EXACTLY ONCE AT STARTUP ---
print("Initializing FinBERT model globally (Loading into memory)...", flush=True)
try:
    # This runs once when the script or module is imported
    NLP_ANALYZER = pipeline('text-classification', model='ProsusAI/finbert')
    print("FinBERT loaded successfully and ready.", flush=True)
except Exception as e:
    print(f"Failed to globalize transformers pipeline. Error: {e}", flush=True)
    NLP_ANALYZER = None

def fetch_and_filter_news(ticker, hours=48, fallback_count=5):
    """Fetches Yahoo Finance RSS news and returns filtered articles."""
    rss_url = f'https://finance.yahoo.com/rss/headline?s={ticker}'
    try:
        req = urllib.request.Request(rss_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            xml_data = response.read()
            
        root = ET.fromstring(xml_data)
        all_articles = []
        for item in root.findall('.//item'):
            title = item.find('title')
            pub_date_str = item.find('pubDate')
            if title is not None and pub_date_str is not None:
                pub_date = parsedate_to_datetime(pub_date_str.text)
                all_articles.append({'title': title.text, 'date': pub_date})
    except Exception as e:
        print(f"Error fetching RSS news for {ticker}: {e}", flush=True)
        return []

    if not all_articles:
        return []

    time_limit = datetime.now(timezone.utc) - timedelta(hours=hours)
    recent_articles = [a for a in all_articles if a['date'] >= time_limit]
    
    if recent_articles:
        return recent_articles
    return all_articles[:fallback_count]

def analyze_sentiment(ticker):
    """Calculates sentiment scores using global analyzer and logs to CSV."""
    if NLP_ANALYZER is None:
        print("  [-] Analyzer not available.", flush=True)
        return None
        
    articles = fetch_and_filter_news(ticker)
    if not articles:
        print(f"  [-] No articles found for {ticker}", flush=True)
        return {"weighted_score": 0.0, "polarized_score": 0.0, "articles_analyzed": 0}
    
    sentiment_map = {'positive': 1.0, 'negative': -1.0, 'neutral': 0.0}
    total_score = 0.0
    polarized_score = 0.0
    polarized_count = 0
    
    for article in articles:
        result = NLP_ANALYZER(article['title'])[0]
        label = result['label'].lower()
        score = sentiment_map.get(label, 0.0)
        
        total_score += score
        if score != 0.0:
            polarized_score += score
            polarized_count += 1
            
    avg_score = round(total_score / len(articles), 2)
    avg_polarized = round((polarized_score / polarized_count), 2) if polarized_count > 0 else 0.0
    
    # --- PATH B: SAVE TO CSV DATA STORE ---
    csv_file = "sentiment_history.csv"
    file_exists = os.path.isfile(csv_file)
    
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(csv_file, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp", "Ticker", "Weighted_Score", "Polarized_Score", "Articles_Count"])
        writer.writerow([current_date, ticker, avg_score, avg_polarized, len(articles)])
        
    print(f"  [+] Logged {len(articles)} articles | W-Score: {avg_score} | P-Score: {avg_polarized}", flush=True)
    
    return {
        "weighted_score": avg_score,
        "polarized_score": avg_polarized,
        "articles_analyzed": len(articles)
    }

if __name__ == "__main__":
    ticker_input = input("Enter ticker to test: ").strip().upper()
    if ticker_input:
        analyze_sentiment(ticker_input)