# ======================
# 1. Imports
# ======================
import yfinance as yf
import requests
from duckduckgo_search import DDGS
from langchain.prompts import PromptTemplate
from langchain.tools import Tool
from langchain_core.prompts import PromptTemplate
from langchain_community.utilities.alpha_vantage import AlphaVantageAPIWrapper
from langchain_community.tools.ddg_search import DuckDuckGoSearchRun
from langchain.schema.runnable import RunnableLambda
from langchain_core.tools import tool
from langchain import hub
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_community import GmailToolkit
from datetime import datetime
from langchain_core.output_parsers import JsonOutputParser
from langchain_google_community.gmail.utils import (
    build_resource_service,
    get_gmail_credentials,
)
from langchain_community.agent_toolkits import GmailToolkit
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field
from langchain.agents import create_react_agent, initialize_agent, AgentType
import os
import markdown
from langchain.agents import initialize_agent, AgentType

# ======================
# 2. Setup & Config
# ======================
import os
from dotenv import load_dotenv

# Load keys from .env file if available
load_dotenv()
# LLM_PROVIDER = "groq"   
LLM_PROVIDER = "gemini"   
def get_llm():
    if LLM_PROVIDER == "gemini":
        return ChatGoogleGenerativeAI(model="gemini-2.0-flash-001", temperature=0)
        # return ChatGoogleGenerativeAI(model="gemini-2.0-flash-001", temperature=0)
    elif LLM_PROVIDER == "groq":
        # return ChatGroq(model="openai/gpt-oss-20b", temperature=0)
        return ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
        # return ChatGroq(model="llama3-70b-8192", temperature=0)
    else:
        raise ValueError("Invalid LLM provider. Use 'gemini' or 'groq'.")

# ======================
# 3. Ticker Symbol Tool
# ======================
ddg_search = DDGS()
prompt_ticker = PromptTemplate(
    input_variables=["company_name", "country_name", "search_result"],
    template="""
    Find the ticker symbol of {company_name} in {country_name}.
    Answer with ONLY the raw ticker symbol (e.g., AAPL, MSFT, RELIANCE).
    Search result: {search_result}
    """,
)
llm_ticker = get_llm()

chain = (
    {
        "search_result": RunnableLambda(
            lambda x: ddg_search.text(
                f"{x['company_name']} {x['country_name']} stock ticker symbol"
            )[0]["body"]
        ),
        "company_name": RunnableLambda(lambda x: x["company_name"]),
        "country_name": RunnableLambda(lambda x: x.get("country_name", "India")),
    }
    | prompt_ticker
    | llm_ticker
)
def get_ticker_symbol(company_name: str, country_name: str = "India") -> str:
    resp = chain.invoke({"company_name": company_name, "country_name": country_name})
    ticker = resp.content.strip()

    # Sanity check
    if " " in ticker or len(ticker) > 10:
        ticker = ticker.split()[-1].replace(".", "").upper()

    # Fallback using yfinance if junk
    if not ticker or ticker.lower() in ["stock", "ticker"]:
        try:
            ticker = yf.Ticker(company_name).info.get("symbol", company_name)
        except Exception:
            ticker = company_name
    return ticker

# ======================
# 4. Data Fetch Tools
# ======================

def get_alpha_vantage_data(ticker: str) -> dict:
    """Fetch company fundamentals, ratios, and metrics from Alpha Vantage."""
    api_key = os.getenv("ALPHAVANTAGE_API_KEY")
    if not api_key:
        return {"error": "Alpha Vantage API key not set."}
    
    url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={api_key}"
    response = requests.get(url)
    return response.json() if response.status_code == 200 else {}

def get_financial_news(company: str, n_results: int = 5) -> list:
    """Fetch recent financial news using DuckDuckGo."""
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(company + " stock financial news", max_results=n_results):
            results.append(r)
    return results

def get_yahoo_finance_data(ticker: str) -> dict:
    """Fetch basic info and last 3 days price history from Yahoo Finance."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info if hasattr(stock, "info") else {}
        hist = stock.history(period="3d")

        return {
            "symbol": ticker,
            "longName": info.get("longName", ""),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "country": info.get("country", ""),
            "currency": info.get("currency", ""),
            "marketCap": info.get("marketCap", None),
            "previousClose": info.get("previousClose", None),
            "currentPrice": info.get("currentPrice", None),
            "history": hist.reset_index().to_dict(orient="records"),
        }
    except Exception as e:
        return {"error": str(e), "symbol": ticker}

# Your existing template
analyst_prompt_template = """
You are an elite financial analyst. The report should be written as of **{current_date}**.
Note:make sure that data used is not be old and not taken from your training data of LLM fabricated or misleading.
[structure of report with {data}]
Using the provided data, generate a professional report with the following sections:

Give as much as the numerical data with context where needed.

1.Research Phase & Analysis Phase  - Collect 5 authoritative, 
                -recent sources; 
                -identify key stakeholders and perspectives.
                - Extract, cross-check and validate information; 
                -resolve conflicting viewpoints.

2.Writing Phase -  Produce a financial report with:

                The expected output is a structured financial report containing:
                Headline

                Executive Summary:  Concise overview of key findings and significance

                Stock info(Get info from Alpha Vantage and
                yahoo_finance_data): change the currency according to the country, stock price, market cap, P/E ratio, dividend yield, 52-week range, 1-year target estimate with source .

                Background & Context: Historical context and importance, Current landscape overview

                Key Findings (with statistics and expert insights): Main discoveries and analysis, Expert insights and quotes, Statistical evidence

                Impact Analysis : Current implications, Stakeholder perspectives, Industry/societal effects

                Future Outlook: Emerging trends, Expert predictions, Potential challenges and opportunities

                Expert Insights: Notable quotes and analysis from industry leaders, Contrasting viewpoints

                Sources & Methodology: List of primary sources with key contributions, Research methodology overview, state link of Sources

3.Quality Control - Verify facts, ensure clarity, readability, and provide context with future implications.
4.Conclusion - Summarize key findings, implications, and recommendations.

Each report is presented in a credit rating style, ensuring reliability, balance, and global context.

# Make the report detailed, fact-checked, and in a professional tone.

# Publication Date: {current_date}
# Data: {data}
# Sources with Link if possible

"""

report_prompt = PromptTemplate.from_template(analyst_prompt_template)



def generate_financial_report(data: str, company_name: str = "", report_type: str = "Financial Analysis") -> dict:
    """
    Generate a comprehensive financial analysis report using the tools Alpha Vantage Data,Yahoo Finance Data and Financial News data.

    Args:
        data: Financial data or information to analyze(manatory come from tools Alpha Vantage Data,  Yahoo Finance Data and Financial News data)
        company_name: Name of the company (mandatory) 
        report_type: Type of report (default: "Financial Analysis")
    
    Returns:
        dict: Contains 'subject', 'body(data should be from Yahoo Finance Data, Alpha Vantage Data, and Financial News data)', 'date', and 'metadata'
    """
    global Final_report
    global subject
    llm = get_llm()
    current_date = datetime.now().strftime("%B %d, %Y")
    
    global report_content
    report_content = llm.invoke(
        report_prompt.format(data=data, current_date=current_date)
    ).content
    
    if company_name:
        subject = f"{company_name}: {report_type} - {current_date}"
    else:
        first_line = report_content.split('\n')[0] if report_content else ""
        if first_line and any(word in first_line.lower() for word in ['inc', 'corp', 'ltd', 'llc']):
            subject = f"{report_type}: {first_line.strip('#').strip()} - {current_date}"
        else:
            subject = f"{report_type} Report - {current_date}"
    global Final_report
    Final_report={
        "subject": subject,
        "body": report_content,
        "date": current_date,
        "metadata": {
            "company": company_name,
            "report_type": report_type,
            "word_count": len(report_content.split()),
            "generated_at": datetime.now().isoformat(),
            "template_used": "analyst_prompt_template"
        }
    }
    return Final_report



def send_mail(recipient:str):
    credentials = get_gmail_credentials(
        token_file="D:/projects/Finance/Ai_Agent/token.json",
        scopes=["https://mail.google.com/"],
        client_secrets_file="D:/projects/Finance/Ai_Agent/credentials-2.json",
    )
    llm = get_llm()
    api_resource = build_resource_service(credentials=credentials)
    toolkit = GmailToolkit(api_resource=api_resource)
    body_html = markdown.markdown(Final_report["body"])
    styled_html = f"""
    <html>
    <body>
        <h1>{subject}</h1>
        <p><strong>Date:</strong> {Final_report['date']}</p>
        <hr>
        {body_html}
        <p><strong>Report Type:</strong> {Final_report['metadata']['report_type']}</p>
    </body>
    </html>"""

    agent = initialize_agent(
        tools=toolkit.get_tools(),
        llm=llm,
        agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
    )
    print(agent.run("Send the mail to " + recipient + " with the following HTML code "   + styled_html))

