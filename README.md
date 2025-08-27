# Financial Report Generator Agent

End-to-end, notebook-driven agent that **fetches market data**, **summarizes news**, **creates a polished financial report**, and **emails it to your recipients** — all in one run.

---

## What it does (at a glance)

- Pulls prices and metrics from **Yahoo Finance** and **Alpha Vantage**.
- Finds fresh headlines using **DuckDuckGo Search**.
- Uses an **LLM (Gemini via `langchain_google_genai`)** to draft narrative insights.
- Renders a **clean, structured HTML report** (optionally PDF/Markdown if you add exporters).
- Sends the report via **Gmail** using LangChain's Google Community toolbox.

All of the above is implemented in `Main_agent.ipynb` so you can tweak, extend, and re-run quickly.

---

## Key capabilities

- **Automated data retrieval**
  - `yfinance` for OHLCV and simple stats
  - `Alpha Vantage` (via `langchain_community.utilities.alpha_vantage`) for additional indicators (requires API key)
- **News & context**
  - `duckduckgo_search` tool (LangChain community) to surface relevant financial/news links
- **LLM commentary**
  - Uses **Google Generative AI (Gemini)** via `langchain_google_genai` to summarize, explain moves, and craft human-like commentary
- **Beautiful email report**
  - Sends an **HTML email** with proper headings, lists, and optional attachments directly through **Gmail** (LangChain Google Community)

---

## Project structure

```
Main_agent.ipynb   # Jupyter Notebook containing the full pipeline
```

> You can keep everything in the notebook or export to a script (see **Run & Automate**).

---

## How it works (architecture)

1. **Ingest**  
   - Pull tickers/time windows from config cells.
   - Fetch price series & metrics from **Yahoo Finance** and/or **Alpha Vantage**.

2. **Enrich**  
   - Grab recent headlines using **DuckDuckGo Search**.
   - Assemble a compact context window for the LLM.

3. **Analyze & Write**  
   - Call **Gemini** (via LangChain) to generate a readable narrative: trends, notable movers, risks, next steps.

4. **Render**  
   - Build a structured **HTML** report (sections, tables, lists).

5. **Deliver**  
   - Send the email (HTML body + optional attachments) via **Gmail** using the `langchain_google_community` helpers.

---

## Custom AI TOOLs

- `get_ticker_symbol(...)` – Normalize/validate a user-entered company/ticker.
- `get_yahoo_finance_data(...)` – Pull OHLCV and Stock Market Data, simple stats with `yfinance`.
- `get_alpha_vantage_data(...)` – Fetch indicators/series Stock Market Data from Alpha Vantage.
- `get_financial_news(...)` – Use DuckDuckGo Search to find recent news.
- `get_llm(...)` – Instantiate the LLM (Gemini via LangChain Google GenAI).
- `generate_financial_report(...)` – Orchestrate data + news + LLM to produce HTML.
- `send_mail(...)` – Deliver the final HTML based structured report via Gmail (LangChain Google Community).

---

## Tech stack

- **Agents/Orchestration**: `langchain`, `langchain_core`, `langchain_community`
- **LLM**: `langchain_google_genai` (Gemini)
- **Gmail**: `langchain_google_community` (plus `googleapiclient` under the hood)
- **Data**: `yfinance`, `langchain_community.utilities.alpha_vantage`
- **Search**: `duckduckgo_search` (LangChain tool)
- **Config**: `python-dotenv`
- **Runtime**: Python 3.10+ recommended

---

## Setup

1. **Create and activate a virtual environment**

   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS/Linux
   source .venv/bin/activate
   ```

2. **Install dependencies**

   ```bash
   pip install -U pip
   pip install pandas numpy yfinance python-dotenv langchain langchain-community                langchain-core duckduckgo-search langchain-google-genai                langchain-google-community
   ```

3. **Environment variables**

   Create a `.env` file in the project root with at least:

   ```dotenv
   # Required for Alpha Vantage utilities
   ALPHAVANTAGE_API_KEY=your_alpha_vantage_key

   # Required for Gemini (LLM) via langchain_google_genai
   GOOGLE_API_KEY=your_google_generative_ai_api_key
   ```

   > **Note on Gmail auth**: The LangChain Gmail tools use the official Gmail API and typically require **OAuth 2.0** credentials (`credentials.json`) and will create/store a `token.json` on first run. Follow the **Gmail API setup** below.

---

## Gmail API setup (for sending email)

1. Go to **Google Cloud Console** → create a project.
2. **Enable the Gmail API**.
3. Create **OAuth 2.0 Client ID** (Desktop App is the easiest for local use).
4. Download `credentials.json` and place it in your project directory.
5. On first run of the notebook’s Gmail cells, a browser window will ask you to authorize the app; a `token.json` will be saved for future runs.

> If you use a different flow (service account, domain-wide delegation) adjust accordingly. The LangChain Google Community Gmail tooling wraps these standard flows.

---

## Configuring your report

- **Tickers & Watchlists** – Set in the config cells. You can pull single tickers or lists.
- **Date range** – Use recent days/weeks for daily notes, or longer windows for monthly/quarterly reviews.
- **Sections** – Edit the HTML builder in `generate_financial_report(...)` to add/remove sections like:
  - Market overview
  - Top movers
  - Key ratios/indicators
  - News highlights with links
  - LLM commentary & next steps

---

## Run & automate

### Run from the notebook
Open `Main_agent.ipynb` and **Run All**.

### Export to a script (optional)

```bash
jupyter nbconvert --to script Main_agent.ipynb
python Main_agent.py
```

### Schedule it
- **Windows Task Scheduler** or **cron** can run the script daily/weekly.
- Ensure your virtual environment and env vars are loaded in the scheduled task.

---

## Email formatting tips (fix “paragraph-like” emails)

If your email lands as one long paragraph, make sure you’re sending **HTML** and include proper tags. For example:

```html
<!DOCTYPE html>
<html>
  <body style="font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;">
    <h2>Daily Financial Brief</h2>
    <p>Good morning! Here’s your summary for <strong>{ date }</strong>.</p>

    <h3>Market Overview</h3>
    <ul>
      <li>S&P 500: { sp_change_pct }%</li>
      <li>NIFTY 50: { nifty_change_pct }%</li>
    </ul>

    <h3>Top Movers</h3>
    <table cellpadding="6" cellspacing="0" border="0">
      <tr><th align="left">Ticker</th><th align="right">Δ%</th></tr>
      { rows }
    </table>

    <h3>News Highlights</h3>
    <ol>
      { news_items }
    </ol>

    <p style="color:#666">Generated by the Financial Report Generator Agent.</p>
  </body>
</html>
```

- Use `<p>`, `<ul>/<ol>`, `<table>` etc.  
- Avoid relying on plain `\n` newlines for email clients.  
- Always set the email **Content-Type** to `text/html` when sending.

---

## Troubleshooting

- **Emails show as raw HTML or as a single paragraph**  
  Ensure the MIME part is `text/html` and your body contains proper HTML tags.

- **Gmail auth errors**  
  Confirm `credentials.json` is present, the Gmail API is enabled, and you completed the OAuth consent once to create `token.json`.

- **Alpha Vantage quota**  
  Free tier is rate-limited. Cache results or add retries/backoff.

- **LLM output quality**  
  Adjust the system prompt in `get_llm(...)` and/or temperature settings to keep the tone factual and concise.

---

## Security

- Never commit `.env`, `credentials.json`, or `token.json` to version control.
- Use least-privilege and rotate credentials regularly.
- Review API usage and costs for all providers.

---

## Extend the agent

- Add new data sources (fundamentals, macro, options) via LangChain tools.
- Enrich the LLM prompt with portfolio context and historical notes.
- Export to **PDF** using `pdfkit` or `weasyprint` if you need an attachment.
- Add charts (PNG) and attach them to the email.

---

## Detected environment keys

- `ALPHAVANTAGE_API_KEY`
- `GOOGLE_API_KEY`

> These are the only keys found directly in code. Gmail auth uses OAuth files (`credentials.json`, `token.json`) rather than an API key.

---

## License

Choose a license (e.g., MIT) and add it here.
