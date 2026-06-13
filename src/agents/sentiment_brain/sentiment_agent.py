import torch
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timedelta, timezone
from transformers import pipeline

def fetch_and_filter_news(ticker, hours=48, fallback_count=5):
    """Fetches RSS news and returns dictionaries containing titles and timestamps."""
    print(f"\nFetching latest news via RSS for {ticker}...")
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
        print(f"Error fetching RSS news for {ticker}: {e}")
        return []

    if not all_articles:
        return []

    time_limit = datetime.now(timezone.utc) - timedelta(hours=hours)
    recent_articles = [a for a in all_articles if a['date'] >= time_limit]
    
    if recent_articles:
        print(f"Found {len(recent_articles)} articles in the last {hours} hours.")
        return recent_articles
    else:
        print(f"No news in the last {hours} hours. Falling back to the {fallback_count} most recent articles.")
        return all_articles[:fallback_count]

def analyze_sentiment():
    print("===========================================")
    print("       AI Sentiment Agent Initialized      ")
    print("===========================================")
    
    ticker = input("Enter a stock ticker symbol to analyze (e.g., AAPL, RELIANCE.NS): ").strip().upper()
    if not ticker:
        print("Invalid ticker. Exiting.")
        return
        
    articles = fetch_and_filter_news(ticker)
    
    if not articles:
        print(f"\nNo valid news found for {ticker}.")
        return
        
    print("Initializing FinBERT (Loading from local cache)...")
    try:
        analyzer = pipeline('text-classification', model='ProsusAI/finbert')
    except Exception as e:
        print(f"\nFailed to initialize the transformers pipeline. Error: {e}")
        return
    
    sentiment_map = {'positive': 1.0, 'negative': -1.0, 'neutral': 0.0}
    
    total_score = 0.0
    polarized_score = 0.0
    polarized_count = 0
    
    print("\n--- News Headlines & Sentiment ---")
    for article in articles:
        title = article['title']
        # Format the date to look clean (e.g., Jun 12, 02:30 PM)
        date_str = article['date'].strftime('%b %d, %I:%M %p %Z')
        
        result = analyzer(title)[0]
        label = result['label'].lower()
        score = sentiment_map.get(label, 0.0)
        
        total_score += score
        if score != 0.0:
            polarized_score += score
            polarized_count += 1
            
        print(f"Time: {date_str}")
        print(f"Headline: {title}")
        print(f"Sentiment: {label.capitalize()} (Score: {score})")
        print("-" * 60)
        
    avg_score = total_score / len(articles)
    avg_polarized = (polarized_score / polarized_count) if polarized_count > 0 else 0.0
    
    print("\n===========================================")
    print(f"  Weighted Market Score (All News): {avg_score:.2f}")
    print(f"  Polarized Signal (Active Emotion): {avg_polarized:.2f}")
    print("===========================================")

if __name__ == "__main__":
    analyze_sentiment()