# PROJECT: Data Analyst Agent
# AUTHOR: Antonio Castañares Rodríguez

# DESCRIPTION: This file implements a Streamlit app that serves as a Marketing Analyst. Every interaction causes Streamlit
# to re-run the entire script. Variables stored in st.session_state and StreamlitChatMessageHistory persist across runs.

import time
import logging
from openai import OpenAI
import streamlit as st
import plotly.io as pio

from marketing_analyst import MarketingAnalyst
from langchain_community.chat_message_histories import StreamlitChatMessageHistory

# --------------------------------------LOGGING--------------------------------------------
# Logging configuration (print time, name, level and message using the terminal)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Suppress the httpx library logs to avoid cluttering the output
logging.getLogger("httpx").setLevel(logging.WARNING)
LOGGER = logging.getLogger(__name__)

# --------------------------------------HELPER_FUNCTIONS------------------------------------

# Display previous messages in each run
def display_chat_history():
    """
    Description: Display chat history including text messages and plots.
    Args: 
        None
    Returns:
        None
    """
    for msg in msgs.messages:                                                                       # Iterate through stored messages
        with st.chat_message(msg.type):                                                             # Display each message in the chat
            if "PLOT_INDEX:" in msg.content:                                                        # Check if the message contains a plot index
                # Replay stored Plotly charts from session state
                plot_index = int(msg.content.split("PLOT_INDEX:")[1])
                st.plotly_chart(
                    st.session_state.plots[plot_index], key=f"history_plot_{plot_index}"
                )
            elif "SQL_INDEX:" in msg.content:                                                       # Check if the message contains a SQL query index
                # Replay stored SQL queries from session state
                sql_index = int(msg.content.split("SQL_INDEX:")[1])
                sql_data = st.session_state.sql_queries[sql_index]
                
                tab1, tab2 = st.tabs(["👨‍💼 AI Analysis", "🔍 SQL Query"])
                with tab1:
                    st.write(sql_data['response'])
                with tab2:
                    st.code(sql_data['query'], language="sql")
            else:                                                                                   # Regular text message
                if msg.type == "ai":
                    st.write(msg.content)
                else:
                    st.write(msg.content)

# --------------------------------------INITIALIZATION--------------------------------------

MODEL_LIST = ["gpt-5-nano", "gpt-4.1-nano", "gpt-4o-mini"]
TITLE = "Marketing Analyst"

st.set_page_config(
    page_title=TITLE,
    page_icon="📊",
)
st.title("🎯 Marketing Analyst AI")


# --------------------------------------SIDEBAR---------------------------------------------

st.markdown("""
            This project demonstrates the **capabilities of Machine Learning and Artificial Intelligence in marketing analytics.** By using language models, we can generate SQL queries, analyze customer segments, and create targeted marketing strategies.

            In detail, this multi-agent AI system implements the following specialized agents:

            - 📋 **Data Overview:** Provides an **introduction to the database** used in this project. Displays column names, data types, brief descriptions of each table, and visualizations to complement the analysis.
            - 🔍 **Data Exploration:** It a **SQL generator that translates natural language into database queries** and interprets insights automatically.
            - 💼 **Business Analysis:** Produces a **business report based on key metrics** such as revenue, average order value, and customer lifetime value (CLV).
            - 📧 **Email Marketing:** Identifies target customers and **creates personalized email campaigns.**
            - 📣 **Marketing Strategy:** Segments customers into clusters and **generates targeted marketing strategies for each group.**

            Use the following examples to get started!
""")

with st.expander("Example Questions", expanded=False):
    st.write(
        """
        📋 **Data Overview**:
        -  Introduce the dataset
        -  Show me the structure of your database

        🔍 **Data Exploration**:
        -  What are the top-selling products by revenue?
        -  Give me the top 5 countries by revenue

        💼 **Business Analysis**:
        -  Give me a complete overview of our business performance
        -  What are the key business insights from the data?

        📧 **Email Marketing**
        -  Write a personalized email for users in segment 4 who don't buy product_id 34, offering a premier access.
        -  Write a promotional email for customers with high lead scores but low purchase frequency.

        📣 **Marketing Strategy**:
        -  Analyze our customer segments
        -  Generate targeted marketing strategies for each segment
        """
    )

# --------------------------------------MODEL_SELECTION-------------------------------------

# Initialize session state for API key validation
if "api_key_valid" not in st.session_state:
    st.session_state.api_key_valid = False

if "OPENAI_API_KEY" not in st.session_state:
    st.session_state["OPENAI_API_KEY"] = ""

# Only show input field if API key is not yet validated
if not st.session_state.api_key_valid:
    st.session_state["OPENAI_API_KEY"] = st.sidebar.text_input(
        "Introduce your OpenAI API Key",
        type="password",
        help="Your OpenAI API key is required for the app to function.",
    )

if st.session_state["OPENAI_API_KEY"]:
    if not st.session_state.api_key_valid:
        # Validate the API key
        try:
            client = OpenAI(api_key=st.session_state["OPENAI_API_KEY"])
            client.models.list()
            st.session_state.api_key_valid = True
            success_key = st.sidebar.success("API Key validated successfully!")
            time.sleep(1)
            success_key.empty()
        except Exception as e:
            st.session_state.api_key_valid = False
            st.sidebar.error(f"Invalid API Key: Please try again.")
            st.stop()
else:
    if not st.session_state.api_key_valid:
        st.info("Please enter your OpenAI API Key to proceed.")
        st.stop()

model_option = st.sidebar.selectbox("Choose a model", MODEL_LIST, index=0)

# Initialize session state variables if they don't exist
if "current_model" not in st.session_state:
    st.session_state.current_model = None
    st.session_state.marketing_analyst = None

# Reinitialize if model changed
if st.session_state.current_model != model_option:
    st.session_state.current_model = model_option
    st.session_state.marketing_analyst = MarketingAnalyst(
        model=model_option, 
        api_key=st.session_state["OPENAI_API_KEY"]
    )
    # Display success message for 1 second
    success_model = st.sidebar.success(f"Initialized with {model_option}")
    time.sleep(1)
    success_model.empty()
    st.rerun()

# Get the marketing analyst instance
marketing_analyst = st.session_state.marketing_analyst

# --------------------------------------CHAT_HISTORY-----------------------------------------

# In each run, access to StreamlitChatMessageHistory to persist chat history across runs
msgs = StreamlitChatMessageHistory(key="langchain_messages")                                        # Previous chat messages
if len(msgs.messages) == 0:                                                                         # If no previous messages, add a welcome message                                         
    msgs.add_ai_message("How can I help you?")

if "plots" not in st.session_state:                                                                 # Initialize session state for storing plots
    st.session_state.plots = []

if "sql_queries" not in st.session_state:                                                           # Initialize session state for storing SQL queries
    st.session_state.sql_queries = []

# Render current messages from StreamlitChatMessageHistory
display_chat_history()

# --------------------------------------CONVERSATION-----------------------------------------

if question := st.chat_input("Enter your question here:", key="query_input"):
    with st.spinner("Thinking..."):                                                                 # Show a message while processing
        st.chat_message("human").write(question)                                                    # Display user message in chat
        msgs.add_user_message(question)                                                             # Adding user message to history      

        try:
            marketing_analyst.invoke_agent(user_instructions=question)                              # Invoke the Marketing Analyst agent   
            result = marketing_analyst.get_response()                                               # Get the response
        except Exception as e:
            st.chat_message("ai").write(f"An error occurred while processing your query: {str(e)}")
            msgs.add_ai_message("An error occurred while processing your query. Please try again.")
            LOGGER.error(f"Error during agent invocation: {e}")
            st.stop()

        if result['next_action'] == 'data_exploration' or result['next_action'] == 'email_writer':
            sql_query = result.get('sql_query')
            response_content = result['response'][0].content

            if sql_query:
                sql_index = len(st.session_state.sql_queries)
                st.session_state.sql_queries.append({
                    'query': sql_query,
                    'response': response_content
                })
                msgs.add_ai_message(f"SQL_INDEX:{sql_index}")
                
                # Display tabs for current interaction
                tab1, tab2 = st.tabs(["👨‍💼 AI Analysis", "🔍 SQL Query"])
                with tab1:
                    with st.chat_message("ai"):
                        st.markdown(response_content)
                    # Display the chart if available
                    chart_json_list = result.get('chart_json')
                    if chart_json_list:
                        for chart_json in chart_json_list:
                            try:
                                plot_obj = pio.from_json(chart_json)
                                plot_index = len(st.session_state.plots)
                                st.session_state.plots.append(plot_obj)
                                msgs.add_ai_message(f"PLOT_INDEX:{plot_index}")
                                st.plotly_chart(plot_obj)
                            except Exception as e:
                                st.warning(f"Could not display chart: {str(e)}")
                with tab2:
                    st.code(sql_query, language="sql")
            else:
                with st.chat_message("ai"):
                    st.markdown(response_content)
                msgs.add_ai_message(response_content)

        else:
            # Display the AI response
            response_content = result['response'][0].content                                            # Get the response content
            with st.chat_message("ai"):
                st.markdown(response_content)                                                           # Display AI message in chat
            msgs.add_ai_message(response_content)                                                       # Add AI message to history

            # Display the chart if available
            chart_json_list = result.get('chart_json')
            if chart_json_list:
                for chart_json in chart_json_list:
                    try:
                        plot_obj = pio.from_json(chart_json)
                        plot_index = len(st.session_state.plots)
                        st.session_state.plots.append(plot_obj)
                        msgs.add_ai_message(f"PLOT_INDEX:{plot_index}")
                        st.plotly_chart(plot_obj)
                    except Exception as e:
                        st.warning(f"Could not display chart: {str(e)}")