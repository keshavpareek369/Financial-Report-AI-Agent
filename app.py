import streamlit as st
import markdown
from datetime import datetime
from tools import (
    get_yahoo_finance_data,
    get_alpha_vantage_data,
    get_financial_news,
    get_ticker_symbol,
    generate_financial_report,
    send_mail,
    get_llm,
)
from langchain.tools import Tool
from langchain import hub
from langchain.agents import create_react_agent, AgentExecutor
from langchain.memory import ConversationBufferMemory
import re

# Page config (must be called before any other Streamlit calls)
st.set_page_config(page_title="Finance Analyst Chatbot", page_icon="💹", layout="wide")

# Sidebar info
st.sidebar.title("About Finance Analyst Agent")
st.sidebar.markdown("""
**Finance Analyst Chatbot** leverages advanced LLMs and real-time financial APIs to answer your finance questions, generate analyst reports, and even send emails with results.

**Capabilities:**
- Fetch stock data from Yahoo Finance and Alpha Vantage
- Get recent financial news
- Find company ticker symbols
- Generate detailed financial reports
- Email reports directly

**How to use:**
- Ask about a company, stock, or financial topic
- Request a report (e.g., "Create a financial report for Apple USA and show me in chat.")
- Ask to send a report via email (e.g., "Send a report to my@email.com")
- **Note:** Report any issue [here](https://github.com/keshavpareek369/Financial-Report-AI-Agent/issues).
""")

# Show current report status in sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("📊 Current Session Status")

# Import the Final_report from tools to check status
try:
    from tools import Final_report
    if Final_report and Final_report.get('body'):
        company = Final_report.get('metadata', {}).get('company', 'Unknown')
        report_date = Final_report.get('date', 'Unknown')
        word_count = Final_report.get('metadata', {}).get('word_count', 0)
        
        st.sidebar.success("✅ Report Available")
        st.sidebar.markdown(f"""
**Company:** {company}  
**Date:** {report_date}  
**Words:** {word_count}  

💡 You can now say:
- "Email this report to xyz@email.com"
- "Send this to my email"
- "Mail the report to someone@domain.com"
        """)
    else:
        st.sidebar.info("ℹ️ No report generated yet")
        st.sidebar.markdown("Generate a report first to enable email functionality.")
except:
    st.sidebar.info("ℹ️ No report generated yet")
    st.sidebar.markdown("Generate a report first to enable email functionality.")

# Tool descriptions
with st.expander("🔧 Agent Tools & Functions", expanded=False):
    st.markdown("""
    - **Yahoo Finance Data**: Fetches basic info and price history.
    - **Alpha Vantage Data**: Provides detailed company/stock data.
    - **Financial News**: Retrieves recent news headlines.
    - **Get Ticker Symbol**: Finds the stock ticker for a company.
    - **Generate Report**: Creates a polished analyst report.
    - **Send Email**: Emails the generated report.
    """)

# Add clear chat button
if st.sidebar.button("🗑️ Clear Chat History"):
    st.session_state.messages = []
    st.session_state.memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True
    )
    st.session_state.agent_executor = None
    st.rerun()

# Main page header
st.title("💹 Finance Analyst Chatbot")
st.markdown("""
Welcome to your AI-powered finance assistant!  
Type your question or request below.  
""")

# Quick action buttons if report exists
try:
    from tools import Final_report
    if Final_report and Final_report.get('body'):
        company = Final_report.get('metadata', {}).get('company', 'Unknown')
        st.info(f"📊 Active Report: **{company}** | Ready to email")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            email_recipient = st.text_input("Quick Email:", placeholder="Enter email address to send report", key="quick_email")
        with col2:
            if st.button("📧 Send Report", key="send_btn"):
                if email_recipient and '@' in email_recipient:
                    # Add to messages as if user typed it
                    st.session_state.messages.append({"role": "user", "content": f"Send the report to {email_recipient}"})
                    st.rerun()
                else:
                    st.error("Please enter a valid email")
except:
    pass

# Agent setup (constructed but not invoked at import time)
custom_tools = [
    Tool(
        name="Yahoo Finance Data",
        func=get_yahoo_finance_data,
        description="Fetch basic info and last 5 days price history from Yahoo Finance. Returns stock data as a dictionary."
    ),
    Tool(
        name="Alpha Vantage Data",
        func=get_alpha_vantage_data,
        description="Get the Ticker Symbol and Fetches detailed stock/company data from Alpha Vantage. Returns company fundamentals and metrics."
    ),
    Tool(
        name="Financial News",
        func=get_financial_news,
        description="Fetch recent financial news using DuckDuckGo. Returns a list of news articles with titles and links."
    ),
    Tool(
        name="Get Ticker Symbol",
        func=get_ticker_symbol,
        description="Finds the ticker symbol of a company. Input: company name and country. Returns: ticker symbol string."
    ),
    Tool(
        name="Generate Report",
        func=generate_financial_report,
        description="""Generate a comprehensive financial analysis report. 
        
        CRITICAL INSTRUCTIONS:
        1. First collect data from Yahoo Finance Data, Alpha Vantage Data, and Financial News tools
        2. Pass ALL collected data to this tool
        3. This tool returns the COMPLETE formatted report as a STRING
        4. You MUST include the ENTIRE report content in your final answer
        5. DO NOT summarize - show the FULL report exactly as returned
        6. The report is already formatted and ready to display
        
        Input: data (string with all financial info), company_name (optional)
        Output: Complete formatted financial report ready to display"""
    ),
    Tool(
        name="Send Email",
        func=send_mail,
        description="""Send the most recently generated financial report via email.
        
        IMPORTANT CONTEXT:
        - This tool accesses the LAST report that was generated in this conversation
        - You do NOT need to specify which report or company - it automatically uses the most recent one
        - The report must be generated BEFORE using this tool
        - If no report exists, the tool will return an error with instructions
        
        Usage examples:
        - User: "Email this report to john@example.com" → You call: send_mail("john@example.com")
        - User: "Send it to my email abc@xyz.com" → You call: send_mail("abc@xyz.com")
        - User: "Mail the report to boss@company.com" → You call: send_mail("boss@company.com")
        
        Input: recipient email address (string)
        Output: Confirmation message with report details
        
        Note: If user says "email this" or "send it", they mean the last generated report."""
    )
]

prompt_REACT = hub.pull("hwchase17/react")

# Enhanced custom suffix for better report handling
CUSTOM_SUFFIX = """
CRITICAL INSTRUCTIONS FOR YOUR RESPONSES:

1. REPORT GENERATION:
   - When using "Generate Report" tool, include the COMPLETE report in your final answer
   - DO NOT write "I have created a report" - SHOW the actual report
   - Include every section and detail from the report

2. EMAIL HANDLING - IMPORTANT:
   - When user says "email this", "send it", "mail the report" they mean the LAST generated report
   - You do NOT need to know which company - the Send Email tool automatically uses the most recent report
   - Just extract the email address and call send_mail(email)
   - Examples:
     * User: "Email this to john@test.com" → Action: send_mail("john@test.com")
     * User: "Send it to my boss" → You need to ask for the email address
     * User: "Mail the report" → You need to ask for the email address

3. CONVERSATION CONTEXT:
   - Remember what was discussed in this conversation
   - If a report was generated about Apple, and user says "email it", you know which report
   - Don't ask "which report?" - use the most recent one

4. DATA QUERIES:
   - Present data clearly with proper formatting
   - Include all relevant numbers and facts

5. Your final answer should be what the user wants to see:
   - Report request → Show FULL report
   - Data request → Show the data  
   - Email request → Confirm sending with details

Remember: Users expect you to maintain context. "This report" = "the report we just discussed"

Begin!

Question: {input}
Thought: {agent_scratchpad}"""

# Apply custom suffix to prompt
try:
    if hasattr(prompt_REACT, 'template'):
        # Replace the default suffix with our custom one
        original_template = prompt_REACT.template
        if "Begin!" in original_template:
            prompt_REACT.template = original_template.split("Begin!")[0] + CUSTOM_SUFFIX
except Exception as e:
    st.sidebar.warning(f"Could not modify prompt template: {e}")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Initialize memory properly
if "memory" not in st.session_state:
    st.session_state.memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True
    )

# Initialize agent in session state
if "agent_executor" not in st.session_state:
    st.session_state.agent_executor = None

# Track last generated report metadata
if "last_report_info" not in st.session_state:
    st.session_state.last_report_info = {
        "company": None,
        "date": None,
        "generated": False
    }

def get_agent_executor():
    """Create or retrieve the agent executor from session state"""
    if st.session_state.agent_executor is None:
        agent = create_react_agent(
            tools=custom_tools,
            llm=get_llm(),
            prompt=prompt_REACT
        )
        st.session_state.agent_executor = AgentExecutor(
            agent=agent,
            tools=custom_tools,
            memory=st.session_state.memory,
            handle_parsing_errors=True,
            verbose=True
        )
    return st.session_state.agent_executor

def format_response(output):
    """Format the agent output for better readability"""
    
    # Check if it's a financial report (contains multiple sections)
    if any(keyword in output.lower() for keyword in ['executive summary', 'financial analysis', 'recommendation', '##', '###']):
        # It's likely a report, render as markdown
        return output
    
    # Parse structured data patterns
    lines = output.split('\n')
    formatted_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            formatted_lines.append('')
            continue
            
        # Check for key-value patterns
        if ':' in line and len(line.split(':')) == 2:
            key, value = line.split(':', 1)
            formatted_lines.append(f"**{key.strip()}:** {value.strip()}")
        # Check for bullet points
        elif line.startswith('-') or line.startswith('*') or line.startswith('•'):
            formatted_lines.append(line)
        # Check for numbered lists
        elif re.match(r'^\d+\.', line):
            formatted_lines.append(line)
        # Check for headers (all caps or title case with certain keywords)
        elif line.isupper() or any(keyword in line.lower() for keyword in ['summary', 'analysis', 'conclusion', 'recommendation']):
            formatted_lines.append(f"\n### {line}\n")
        else:
            formatted_lines.append(line)
    
    return '\n'.join(formatted_lines)

def display_structured_output(output):
    """Display output with proper structure and formatting"""
    
    # Check if output is very short (likely just a summary statement)
    if len(output) < 300 and ("created" in output.lower() or "generated" in output.lower()):
        st.warning("⚠️ The agent provided a summary instead of full content. This may indicate an issue with the report generation.")
        st.info("💡 Tip: Try asking 'Show me the complete financial report for [Company]' or 'Display the full analysis for [Company]'")
    
    # Check if it's a report (look for multiple headers and substantial content)
    is_report = (
        len(output) > 500 and
        (output.count('#') > 2 or output.count('**') > 5) and
        any(keyword in output.lower() for keyword in ['executive summary', 'analysis', 'financial', 'recommendation'])
    )
    
    if is_report:
        # It's a full report - display prominently
        st.markdown("## 📊 Financial Analysis Report")
        st.markdown("---")
        st.markdown(output)
        st.markdown("---")
        
        # Add download button for reports
        st.download_button(
            label="📥 Download Report (Markdown)",
            data=output,
            file_name=f"financial_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown"
        )
        
        # Also offer HTML version
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; max-width: 900px; margin: auto; }}
                h1, h2, h3 {{ color: #2c3e50; }}
                table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                th {{ background-color: #3498db; color: white; }}
            </style>
        </head>
        <body>
            {markdown.markdown(output)}
        </body>
        </html>
        """
        st.download_button(
            label="📥 Download Report (HTML)",
            data=html_content,
            file_name=f"financial_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
            mime="text/html"
        )
    
    # Check if output contains financial data patterns
    elif any(indicator in output.lower() for indicator in ['price', 'ticker', 'market cap', 'volume', 'pe ratio', 'dividend']):
        with st.expander("📊 Financial Data", expanded=True):
            st.markdown(format_response(output))
    
    # Check if it's a news response
    elif 'news' in output.lower() or 'headline' in output.lower():
        with st.expander("📰 Latest News", expanded=True):
            st.markdown(format_response(output))
    
    # Check if it's an email confirmation
    elif 'email' in output.lower() and ('sent' in output.lower() or 'delivered' in output.lower()):
        st.success(output)
    
    # Default display
    else:
        st.markdown(format_response(output))

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            display_structured_output(msg["content"])
        else:
            st.write(msg["content"])

# Chat input
user_input = st.chat_input("Ask a financial question, request a report, or email it!")

if user_input:
    # Pre-check: If user is trying to email but no report exists, show helpful message
    if any(keyword in user_input.lower() for keyword in ['email', 'send', 'mail']) and \
       not st.session_state.last_report_info.get("generated", False):
        try:
            from tools import Final_report
            if not Final_report or not Final_report.get('body'):
                st.warning("⚠️ No report has been generated yet. Please create a report first.")
                st.info("💡 Try: 'Create a financial report for Apple and email it to xyz@example.com'")
                # Don't process further
                user_input = None
        except:
            st.warning("⚠️ No report has been generated yet. Please create a report first.")
            st.info("💡 Try: 'Create a financial report for Apple and email it to xyz@example.com'")
            user_input = None

if user_input:
    # Display user message
    with st.chat_message("user"):
        st.write(user_input)
    
    # Add to message history
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Generate assistant response
    with st.chat_message("assistant"):
        with st.spinner("🔍 Analyzing your request..."):
            try:
                executor = get_agent_executor()
                
                # Enable verbose mode to see what's happening
                result = executor.invoke({"input": user_input})
                
                # Extract output
                if isinstance(result, dict):
                    output = result.get("output", str(result))
                    
                    # Debug: Show intermediate steps in expander
                    if "intermediate_steps" in result and st.sidebar.checkbox("🔍 Show Debug Info", value=False):
                        with st.expander("🔧 Agent Debug Information"):
                            st.write("**Intermediate Steps:**")
                            for i, step in enumerate(result["intermediate_steps"]):
                                st.write(f"**Step {i+1}:**")
                                if len(step) >= 2:
                                    st.write(f"- Action: {step[0]}")
                                    st.write(f"- Result length: {len(str(step[1]))} chars")
                                    # Show first 200 chars of result
                                    st.code(str(step[1])[:200] + "..." if len(str(step[1])) > 200 else str(step[1]))
                    
                elif isinstance(result, list):
                    output = "\n".join(map(str, result))
                else:
                    output = str(result)
                
                # Check if output is suspiciously short for a report request
                if "report" in user_input.lower() and len(output) < 1000:
                    st.warning("⚠️ The response seems shorter than expected for a report. Checking intermediate steps...")
                    
                    # Try to extract from intermediate steps
                    if "intermediate_steps" in result:
                        for step in result["intermediate_steps"]:
                            if len(step) >= 2:
                                tool_name = str(step[0]) if len(step[0]) > 0 else ""
                                tool_output = str(step[1])
                                
                                # If we find a "Generate Report" tool with long output, use that
                                if "generate" in tool_name.lower() and len(tool_output) > 1000:
                                    output = tool_output
                                    st.success("✅ Retrieved full report from tool output!")
                                    break
                
                # Display formatted response
                display_structured_output(output)
                
                # Track if a report was generated
                if "report" in user_input.lower() and "generate" in user_input.lower() or "create" in user_input.lower():
                    # Try to extract company name from user input or output
                    try:
                        from tools import Final_report
                        if Final_report and Final_report.get('body'):
                            company = Final_report.get('metadata', {}).get('company', 'Unknown')
                            st.session_state.last_report_info = {
                                "company": company,
                                "date": Final_report.get('date'),
                                "generated": True
                            }
                            st.sidebar.success(f"✅ Report for {company} is ready to email!")
                    except:
                        pass
                
                # Store in history
                st.session_state.messages.append({"role": "assistant", "content": output})
                
            except Exception as e:
                error_msg = f"❌ **Error occurred:** {str(e)}"
                st.error(error_msg)
                
                # Show traceback in expander for debugging
                import traceback
                with st.expander("🐛 Error Details"):
                    st.code(traceback.format_exc())
                
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray; font-size: 0.9em;'>
    Built with LangChain & Streamlit | Powered by AI
    </div>
    """,
    unsafe_allow_html=True
)