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

def display_chat_history():
    """
    Description: Display chat history including text messages and plots.
    Safely replay plots and SQL queries stored in session state. If an index stored in the
    message is missing or invalid, show a warning instead of raising an exception.

    Args:
        None
    Returns:
        None
    """
    for msg in msgs.messages:                                                                                   # Iterate through stored messages
        with st.chat_message(msg.type):                                                                         # Display each message in the chat
            # Replay Plotly charts if a plot index marker was stored
            if msg.content.startswith("PLOT_INDEX:"):
                try:
                    plot_index = int(msg.content.split("PLOT_INDEX:", 1)[1])                                    # Extract plot index
                    if "plots" in st.session_state and 0 <= plot_index < len(st.session_state.plots):           # Check if plot index is valid
                        st.plotly_chart(st.session_state.plots[plot_index], key=f"history_plot_{plot_index}")   # Display the plot
                    else:
                        st.warning(f"Plot not available (index={plot_index}).")
                except Exception as e:
                    st.warning(f"Could not replay plot: {e}")

            # Replay stored SQL queries if a SQL index marker was stored
            elif msg.content.startswith("SQL_INDEX:"):                                                          # Replay stored SQL queries if a SQL index marker was stored
                try:
                    sql_index = int(msg.content.split("SQL_INDEX:", 1)[1])                                      # Extract SQL index
                    if ("sql_queries" in st.session_state and 0 <= sql_index < len(st.session_state.sql_queries)):
                        sql_data = st.session_state.sql_queries[sql_index]                                      # Retrieve SQL query and response
                        tab1, tab2 = st.tabs(["👨‍💼 AI Response", "🔍 SQL Query"])                               # Create the tabs
                        with tab1:
                            st.write(sql_data.get("response", ""))                                              # Display AI Response
                        with tab2:
                            st.code(sql_data.get("query", ""), language="sql")                                  # Display the SQL query
                    else:
                        st.warning(f"SQL query not available (index={sql_index}).")
                except Exception as e:
                    st.warning(f"Could not replay SQL query: {e}")

            # Regular text message
            else:
                st.write(msg.content)

def display_plots(result):
    """
    Description: Display available plots from the result and store them in session state.
    Args:
        result (dict): Result dictionary containing chart JSONs.
    Returns:
        None
    """
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

if "api_key_valid" not in st.session_state:                                                         # Initialize session state for API key validation
    st.session_state.api_key_valid = False

if "OPENAI_API_KEY" not in st.session_state:                                                        # Initialize session state for OpenAI API key 
    st.session_state["OPENAI_API_KEY"] = ""

if not st.session_state.api_key_valid:                                                              # Only show input field if API key is not yet validated
    st.session_state["OPENAI_API_KEY"] = st.sidebar.text_input(
        "Introduce your OpenAI API Key",
        type="password",
        help="Your OpenAI API key is required for the app to function.",
    )

if st.session_state["OPENAI_API_KEY"]:                                                              # If an API key is provided, check its validity
    if not st.session_state.api_key_valid:
        try:
            client = OpenAI(api_key=st.session_state["OPENAI_API_KEY"])                             # Initialize OpenAI client and validate API key by operation
            client.models.list()
            st.session_state.api_key_valid = True                                                   # Set API key as valid
            success_key = st.sidebar.success("API Key validated successfully!")                     # Display success message for 1 second
            time.sleep(1)
            success_key.empty()
        except Exception as e:                                                                      # If validation fails, show error and reset flag 
            st.session_state.api_key_valid = False
            st.sidebar.error(f"Invalid API Key: Please try again.")
            st.stop()
else:
    if not st.session_state.api_key_valid:                                                          # If no API key is provided, prompt user to enter one
        st.info("Please enter your OpenAI API Key to proceed.")                                     
        st.stop()   

model_option = st.sidebar.selectbox("Choose a model", MODEL_LIST, index=0)                          # Model selection 

if "current_model" not in st.session_state:                                                         # Initialize session state variables if they don't exist                                         
    st.session_state.current_model = None
    st.session_state.marketing_analyst = None

if st.session_state.current_model != model_option:                                                  # Reinitialize if model changed
    st.session_state.current_model = model_option                                                   # Update current model in session state
    st.session_state.marketing_analyst = MarketingAnalyst(                                          # Initialize Marketing Analyst agent with a selected model and API key
        model=model_option, 
        api_key=st.session_state["OPENAI_API_KEY"]
    )
    success_model = st.sidebar.success(f"Initialized with {model_option}")                          # Display success message for 1 second
    time.sleep(1)
    success_model.empty()
    st.rerun()                                                                                      # Rerun to apply changes to remove the API key input field

marketing_analyst = st.session_state.marketing_analyst                                              # Get the marketing analyst instance

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

        if result['next_action'] == 'data_exploration' or result['next_action'] == 'email_writer':  # If the action involves SQL queries
            sql_query = result.get('sql_query')                                                     # Get the generated SQL query
            response_content = result['response'][0].content                                        # Get the response content

            if sql_query:                                                                           
                sql_index = len(st.session_state.sql_queries)                                       # Store the SQL query and response in session state
                st.session_state.sql_queries.append({
                    'query': sql_query,
                    'response': response_content
                })
                msgs.add_ai_message(f"SQL_INDEX:{sql_index}")                                       # Add the SQL query and the response to chat history                                        
                
                tab1, tab2 = st.tabs(["👨‍💼 AI Response", "🔍 SQL Query"])                           # Display in one table the response and the another the SQL query
                with tab1:                                                                          # Tab for AI Response
                    with st.chat_message("ai"):
                        st.markdown(response_content)                                               # Display AI message in chat
                        display_plots(result)                                                       # Display available plots
                with tab2:                                                                          # Tab for SQL query 
                    st.code(sql_query, language="sql")                                              # Display the SQL query
            else:                                                                                   
                with st.chat_message("ai"):
                    st.markdown(response_content)                                                   # Display AI message in chat
                    display_plots(result)                                                           # Display available plots
                msgs.add_ai_message(response_content)                                               # Add the response to chat history                                                   

        else:
            # Display the AI response
            response_content = result['response'][0].content                                        # Get the response content
            with st.chat_message("ai"):
                st.markdown(response_content)                                                       # Display AI message in chat
                display_plots(result)                                                               # Display available plots
            msgs.add_ai_message(response_content)                                                   # Add AI message to history