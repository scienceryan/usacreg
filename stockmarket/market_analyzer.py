import pandas as pd
import yfinance as yf
import requests
from io import StringIO
import matplotlib.pyplot as plt
from scipy.stats import theilslopes
import numpy as np
import os

# Configuration: Set your results directory here
RESULTS_DIR = os.path.expanduser("~/Documents/python code/stockmarket")  # Change this to your preferred directory


def get_nasdaq100_tickers():
    """Fetch NASDAQ-100 tickers from Wikipedia"""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    nasdaq100_url = "https://en.wikipedia.org/wiki/Nasdaq-100"
    response = requests.get(nasdaq100_url, headers=headers)
    tables = pd.read_html(StringIO(response.text))
    nasdaq100_df = tables[4]
    
    tickers = nasdaq100_df['Ticker'].tolist()
    companies = dict(zip(nasdaq100_df['Ticker'], nasdaq100_df['Company']))
    
    return tickers, companies


def get_sp100_tickers():
    """Fetch S&P 100 tickers from Stock Analysis"""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    sp500_url = "https://stockanalysis.com/list/sp-500-stocks/"
    response = requests.get(sp500_url, headers=headers)
    sp500_table = pd.read_html(StringIO(response.text))
    sp100_df = sp500_table[0].head(100)
    
    tickers = sp100_df['Symbol'].tolist()
    companies = dict(zip(sp100_df['Symbol'], sp100_df['Company Name']))
    
    return tickers, companies


def fetch_stock_data(tickers, companies):
    """Fetch financial data for given tickers"""
    records = []
    
    for ticker in tickers:
        try:
            apiticker = ticker.replace(".", "-")
            print(f"Fetching info for {apiticker}: ", end="")
            stock = yf.Ticker(apiticker)
            fast_info_data = stock.fast_info
            
            income_stmt = stock.quarterly_income_stmt
            
            if income_stmt.empty:
                raise ValueError(f"No quarterly income statement data found for {apiticker}")
            
            incomeTTM = income_stmt.loc["Net Income"].head(4).sum()
            PEratio = stock.fast_info.market_cap / incomeTTM
            
            print(f"${fast_info_data['last_price']:.2f} | ${fast_info_data['market_cap']/1_000_000_000:.3f}B | {PEratio:.2f}")
            
            records.append({
                "Ticker": ticker,
                "Company": companies[ticker],
                "LastPrice": fast_info_data['last_price'],
                "MarketCap": fast_info_data['market_cap'],
                "Net Income": incomeTTM,
                "P/E TTM": PEratio
            })
        except Exception as e:
            print(f"Error fetching {ticker}: {e}")
    
    return pd.DataFrame(records)


def clean_and_prepare_data(df):
    """Clean data and prepare for analysis"""
    df.reset_index(drop=True, inplace=True)
    df.sort_values(by='MarketCap', ascending=False, inplace=True)
    
    # Filter out companies with negligible or negative net income
    rows_to_drop = df["Net Income"] < 1
    df_clean = df[~rows_to_drop]
    
    return df_clean


def plot_power_law(df_clean, title):
    """Create power law plot with Theil-Sen regression"""
    y = df_clean["Net Income"]
    x = df_clean["MarketCap"]
    names = df_clean["Ticker"]
    
    # Linearize the power law data
    log_x = np.log10(x)
    log_y = np.log10(y)
    
    # Apply Theil-Sen
    k_ts, intercept_ts, low_slope, high_slope = theilslopes(log_y, log_x)
    
    # Transform back to power law parameters
    k = k_ts
    a = 10**intercept_ts
    
    # Generate points for the fitted curve
    x_fit = np.logspace(np.log10(x.min()), np.log10(x.max()), 100)
    y_fit = a * np.power(x_fit, k)
    
    # Create plot
    plt.figure(figsize=(10, 6))
    plt.scatter(x, y, color='royalblue', s=40, alpha=0.7, edgecolors='k')
    
    # Label each point with company name
    for i in range(len(names)):
        plt.text(x.iloc[i], y.iloc[i] * 1.08, names.iloc[i], fontsize=6, ha='center')
    
    # Power law fit line
    plt.plot(x_fit, y_fit, 'r--', label=f'Power Law Fit\n$y = {a:.2e} \cdot x^{{{k:.2f}}}$')
    
    plt.xlim(x.min() * 0.3, x.max() * 3)
    plt.xscale("log")
    
    plt.ylim(y.min() * 0.3, y.max() * 3)
    plt.yscale("log")
    
    plt.title(title)
    plt.xlabel("Market Capitalization")
    plt.ylabel("Net Income")
    plt.grid(True, which="both", ls="--", alpha=0.6)
    plt.legend()
    plt.tight_layout()
    plt.draw()  # Draw the figure
    plt.pause(0.001)  # Small pause to allow rendering


def plot_cumulative_marketcap(df, title):
    """Plot cumulative market cap distribution"""
    df_sorted = df.sort_values(by='MarketCap', ascending=False).reset_index(drop=True)
    total_marketcap = df_sorted['MarketCap'].sum()
    df_sorted['CumPercent'] = (df_sorted['MarketCap'].cumsum() / total_marketcap) * 100
    
    plt.figure(figsize=(10, 6))
    plt.plot(range(len(df_sorted)), df_sorted['CumPercent'], linewidth=2)
    plt.xlabel('Number of Companies (ranked by market cap)')
    plt.ylabel('Cumulative Market Cap (%)')
    plt.title(f'{title} - Market Cap Concentration')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.draw()  # Draw the figure
    plt.pause(0.001)  # Small pause to allow rendering

def analyze_index(index_name, use_cached=True):
    """Main analysis function that selects data source based on index name
    
    Args:
        index_name: 'NASDAQ100' or 'SP100'
        use_cached: If True, load from CSV if it exists. If False, always fetch fresh data.
    """
    
    # Change to results directory
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.chdir(RESULTS_DIR)
    print(f"Working directory set to: {os.getcwd()}\n")
    
    # Programmatically select data source
    if index_name.upper() == "NASDAQ100":
        csv_filename = "nasdaq100.csv"
        plot_title = "NASDAQ 100"
    elif index_name.upper() == "SP100":
        csv_filename = "sp100.csv"
        plot_title = "S&P 100"
    else:
        raise ValueError("Invalid index name. Choose 'NASDAQ100' or 'SP100'")
    
    # Check if CSV exists and use_cached is True
    csv_path = os.path.join(RESULTS_DIR, csv_filename)
    
    if use_cached and os.path.exists(csv_path):
        print(f"Loading cached data from: {csv_path}")
        df = pd.read_csv(csv_path)
        print(f"✓ Loaded {len(df)} companies from cache\n")
    else:
        # Fetch fresh data
        print(f"Fetching {index_name.upper()} data...\n")
        
        if index_name.upper() == "NASDAQ100":
            tickers, companies = get_nasdaq100_tickers()
        elif index_name.upper() == "SP100":
            tickers, companies = get_sp100_tickers()
        
        df = fetch_stock_data(tickers, companies)
        df = df[df['Ticker'] != 'GOOG'].reset_index(drop=True) # Exclude GOOG since its a duplicate of GOOGL
        df.sort_values(by='MarketCap', ascending=False, inplace=True)
        
        # Save to CSV
        df.to_csv(csv_filename, index=False)
        print(f"\n✓ Data saved to: {os.path.abspath(csv_filename)}")
    
    # Display top 25 companies
    print("\nTop 25 companies by market cap:")
    print(df.head(25))
    total_all = df['MarketCap'].sum()
    total_top_25 = df.nlargest(int(len(df) * 0.25), 'MarketCap')['MarketCap'].sum()
    total_bottom_75 = df.nsmallest(int(len(df) * 0.75), 'MarketCap')['MarketCap'].sum()
    print(f"Total market cap: ${total_all/1e12:.2f}T")
    print(f"Top 25%: ${total_top_25/1e12:.2f}T ({total_top_25/total_all*100:.1f}%)")
    print(f"Bottom 75%: ${total_bottom_75/1e12:.2f}T ({total_bottom_75/total_all*100:.1f}%)")
    
    
    # Clean data and create plot
    df_clean = clean_and_prepare_data(df)
    plot_power_law(df_clean, plot_title)
    plot_cumulative_marketcap(df, plot_title)
    
    return df


if __name__ == "__main__":
    # Prompt user to select the index
    while True:
        print("\nSelect an index to analyze:")
        print("1. NASDAQ 100")
        print("2. S&P 100")
        choice = input("Enter your choice (1 or 2): ").strip()
        
        if choice in ["1", "2"]:
            INDEX_TO_ANALYZE = "NASDAQ100" if choice == "1" else "SP100"
            break
        else:
            print("Invalid choice. Please enter 1 or 2.")
    
    # Ask about using cached data
    while True:
        use_cache = input("Use cached data if available? (y/n): ").strip().lower()
        if use_cache in ['y', 'n', 'yes', 'no']:
            USE_CACHED_DATA = use_cache in ['y', 'yes']
            break
        else:
            print("Invalid input. Please enter 'y' or 'n'.")
    
    df_result = analyze_index(INDEX_TO_ANALYZE, use_cached=USE_CACHED_DATA)
        # Keep all plot windows open
    plt.show()  # This blocks and keeps all windows open until closed