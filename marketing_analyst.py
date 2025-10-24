# PROJECT: Marketing Analyst Agent
# AUTHOR: Antonio Castañares Rodríguez

# DESCRIPTION: This file implements a Marketing Analyst agent, which analyzes 
# customer segments and provides insights and marketing implications.

# --------------------------------------IMPORTS--------------------------------------------
import os
import json
import duckdb
import logging

from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama 
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END
from typing import List, Sequence, TypedDict, Literal
from pydantic import BaseModel
from data_manager import DataManager
from prompts import DATA_OVERVIEW_PROMPT, BUSINESS_ANALYST_PROMPT, MARKETING_ANALYST_PROMPT, BEST_EMAILS_PROMPT, WRITE_EMAILS_PROMPT
from prompts import ROUTER_PROMPT, QUERY_GENERATOR_PROMPT, DATA_EXPLORER_PROMPT, PLOT_SELECTION_PROMPT
from generate_plots import PlotGenerator

# --------------------------------------LOGGING--------------------------------------------
# Logging configuration (print time, name, level and message using the terminal)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Suppress the httpx library logs to avoid cluttering the output
logging.getLogger("httpx").setLevel(logging.WARNING)
LOGGER = logging.getLogger(__name__)

# --------------------------------------AUXILIARY_FUNCTIONS-------------------------------

def get_dataset_info_json(df):
    """
    Description: Convert DataFrame metadata to JSON format for LLM.
    Args:
        df (pd.DataFrame): The DataFrame to analyze
    Returns:
        str: JSON string with dataset information
    """

    dataset_info = {
        'row_count': len(df),
        'column_count': len(df.columns),
        'columns': {
            col: {
                'dtype': str(df[col].dtype),
                'non_null_count': int(df[col].count()),
                'null_count': int(df[col].isna().sum()),
                'null_percentage': round(df[col].isna().sum() / len(df) * 100, 2),
                'unique_count': int(df[col].nunique()),
                'sample_values': df[col].dropna().head(3).tolist()
            } for col in df.columns
        },
        'memory_usage_mb': round(df.memory_usage(deep=True).sum() / 1024**2, 2)
    }
    return json.dumps(dataset_info, indent=2)                                                   # Convert to JSON string

def select_visualizations(user_message: str, model, api_key=None) -> dict:
    """
    Description: Select best visualizations from pregenerated plots.
    Args:
        user_message (str): The user's question or message
        model: The LLM model to use for selection
        api_key (str, optional): OpenAI API key for session isolation
    Returns:
        dict: Dictionary with selected plot titles and paths, if no plots selected returns empty lists
    """
    try:
        models = get_models(api_key)                                                        # Get model instances with API key
        llm = models[model]                                                                 # Get the LLM model
        prompt_template = ChatPromptTemplate.from_template(PLOT_SELECTION_PROMPT)           # Load prompt template
        agent = prompt_template | llm | JsonOutputParser()                                  # Create agent with JSON output parser

        result = agent.invoke({'user_message': user_message,                                # Invoke with user message and available plots
                               'available_plots': json.dumps(PlotGenerator().get_plots())})
        
        # Ensure result is a dict and has required keys
        if not isinstance(result, dict):   
            LOGGER.warning(f"LLM returned non-dict result: {type(result)}")
            return {'selected_plots': [], 'paths': []}                                      # Return empty lists if invalid

        # For debugging purposes
        selected_titles = result.get('selected_plots')
        LOGGER.info(f"Selected {len(selected_titles)} plots: {selected_titles}")

        return result
    except Exception as e:
        LOGGER.error(f"Error in select_visualizations: {e}")
        return {'selected_plots': [], 'paths': []}

def load_chart_json(path: str) -> str:
    """
    Description: Load Plotly chart JSON from file.
    Args:
        path (str): File path to the chart JSON
    Returns:
        str: JSON string of the chart, or empty string if error occurs
    """
    try:
        with open(path, 'r') as f:
            chart_json = f.read()
        return chart_json
    except Exception as e:
        LOGGER.error(f"Error loading chart JSON from {path}: {e}")
        return ""

# -------------------------------------MODELS----------------------------------------------

def get_models(api_key=None):
    """
    Create model instances with optional API key for multi-user isolation.
    
    Args:
        api_key (str, optional): OpenAI API key for session isolation
    
    Returns:
        dict: Dictionary of model instances
    """
    models = {
        'llama3.1': ChatOllama(model='llama3.1:8b'),
        'gpt-oss:20b': ChatOllama(model='gpt-oss:20b'), 
        'gpt-5-nano': ChatOpenAI(model='gpt-5-nano', api_key=api_key) if api_key else ChatOpenAI(model='gpt-5-nano'),
        'gpt-4.1-nano': ChatOpenAI(model='gpt-4.1-nano', api_key=api_key) if api_key else ChatOpenAI(model='gpt-4.1-nano'),
        'gpt-4o-mini': ChatOpenAI(model='gpt-4o-mini', api_key=api_key) if api_key else ChatOpenAI(model='gpt-4o-mini')
    }
    return models

# -------------------------------------VARIABLES-------------------------------------------

db_path = 'data/leads_scored.db'                                                            # Path to the SQLite database                                                        
marketing_path = 'marketing_graph.png'                                                      # Path to save marketing graph image

class Route(BaseModel):
    '''
    Description: Route to next step in the LangGraph workflow
    '''
    next: Literal['data_overview', 'data_exploration', 'email_writer',                      # next can be only one of these specified options
                  'business_analysis', 'marketing_analysis']
  
# -------------------------------------STATE-----------------------------------------------

class State(TypedDict):
    message: Sequence[BaseMessage]                                                          # Chat history      
    response: Sequence[BaseMessage]                                                         # Response from the agent
    insights: str                                                                           # Insights from the marketing analysis
    summary_table: str                                                                      # Summary table in JSON format
    chart_json: List[str]                                                                   # List of chart JSON strings
    model: str                                                                              # Model used for all agents
    api_key: str                                                                            # OpenAI API key for session isolation
    data_manager: DataManager                                                               # DataManager instance to avoid several loads
    next_action: str                                                                        # Next action decided by the router
    sql_query: str                                                                          # Generated SQL query 

# --------------------------------------NODES----------------------------------------------

def router_node(state: State):
    """
    Description: Decides the next step: data_overview, data_exploration or marketing_analysis
    Args:
        state (State): The current state of the workflow.
    Return:
        dict: Dictionary with the next action decided by the router, if routing fails defaults to data_overview
    """

    last_message = state.get('message', [])[-1] if state.get('message') else None           # Get the last user message for routing decision

    if not last_message:                                                                    # If not user's message, provide data overview 
        LOGGER.info("No user message found, defaulting to data_overview.")
        return {'next_action': 'data_overview'}
    
    # Prepare prompt for routing decision
    formatted_prompt = ROUTER_PROMPT.format(user_question=last_message.content)            
    messages = [{'role': 'system', 'content': formatted_prompt}]
    
    try:
        # Decides the next node based on the last user's message
        models = get_models(state.get('api_key'))
        llm = models[state.get('model')] 
        response = llm.with_structured_output(Route).invoke(messages)                       # response = ['data_overview' or 'data_exploration' or 'business_analysis' or 'marketing_analysis']
        LOGGER.info(f'Router decided: {response.next}')
        return {'next_action': response.next}
    except Exception as e:
        LOGGER.error(f'Router Node Error: {e}')
        # Default to respond if routing fails
        return {'next_action': 'data_overview'}
    
def route_after_router(state: State):
    """
    Description: Function used as conditional_edge after router_node
    Args:
        state (State): The current state of the workflow.
    Return:
        str: The next action to be taken.
    """

    return state['next_action']

def DataOverview_node(state: State):
    """
    Description: Provide an overview of the datasets.
    Args:
        state (State): The current state of the workflow.
    Return:
        dict: A dictionary containing the overview of the datasets and possible interesting visualizations.
    """

    # Load DataFrames 
    data_manager = state.get('data_manager')
    leads_scored = data_manager.leads
    transactions = data_manager.transactions
    products = data_manager.products

    # Prepare dataset info and descriptions in JSON format for LLM
    leads_scored_info = get_dataset_info_json(leads_scored)
    transactions_info = get_dataset_info_json(transactions)
    products_info = get_dataset_info_json(products)
    leads_scored_describe = leads_scored.describe().to_json(orient='columns')
    transactions_describe = transactions.describe().to_json(orient='columns')
    products_describe = products.describe().to_json(orient='columns')

    # Prepare and invoke LLM agent
    models = get_models(state.get('api_key'))
    llm = models[state.get('model')] 
    prompt_template = ChatPromptTemplate.from_template(DATA_OVERVIEW_PROMPT)
    agent = prompt_template | llm

    messages = state.get('message', [])
    last_question = messages[-1].content if messages else "Provide comprehensive data analysis"

    # Invoke with all the data the prompt expects
    result = agent.invoke({
        'initial_question': last_question,
        'leads_scored_info': leads_scored_info,
        'transactions_info': transactions_info,
        'products_info': products_info,
        'leads_scored_describe': leads_scored_describe,
        'transactions_describe': transactions_describe,
        'products_describe': products_describe
    })

    # Load chart JSON for any relevant visualizations
    relevant_plots = select_visualizations(last_question, state.get('model'), state.get('api_key'))
    
    chart_json = []
    if relevant_plots and relevant_plots.get('paths'):                                      # Check if dict exists AND paths is not empty   
        for path in relevant_plots['paths']:
            chart_json.append(load_chart_json(path))                                        # Load each chart JSON and append to list

    LOGGER.info("Data overview completed successfully.")
    LOGGER.info("=" * 40)

    return {
        'response': [AIMessage(content=result.content)],
        'chart_json': chart_json if chart_json else None
    }

def DataExplorer_node(state: State):
    """
    Description: Execute SQL queries on DataFrames using DuckDB based on user questions.
    Args:
        state (State): The current state of the workflow.
    Return:
        dict: A dictionary containing the response from the LLM, executed SQL query, and any relevant chart JSONs.
    """

    models = get_models(state.get('api_key'))
    llm = models[state.get('model')] 
    
    # Step 1: Generate SQL query from user question
    prompt_template = ChatPromptTemplate.from_template(QUERY_GENERATOR_PROMPT)
    query_agent = prompt_template | llm

    messages = state.get('message', [])
    last_question = messages[-1].content if messages else "No query requested"

    # Generate SQL query
    query_response = query_agent.invoke({'initial_question': last_question})

    LOGGER.info(f"Generated SQL Query: \n{query_response.content}")

    # Load DataFrames
    data_manager = state.get('data_manager')
    leads_scored = data_manager.leads
    transactions = data_manager.transactions
    products = data_manager.products

    # Step 2: Execute SQL query using DuckDB
    try:
        query_result_df = duckdb.query(query_response.content).to_df()                      # DuckDB automatically detects DataFrames in the local scope
        query_result_json = query_result_df.to_json(orient='records')
        LOGGER.info(f"Query executed successfully. Result rows: {len(query_result_df)}")
    except Exception as e:
        LOGGER.error(f"DuckDB Query Error: {e}")
        error_message = "Please rephrase your question or try a different approach."
        return {'response': [AIMessage(content=error_message)]}

    # Step 3: Analyze query results with LLM
    prompt_template = ChatPromptTemplate.from_template(DATA_EXPLORER_PROMPT)
    analysis_agent = prompt_template | llm

    result = analysis_agent.invoke({
        'initial_question': last_question,
        'sql_query': query_response.content,
        'query_result': query_result_json
    })

    # Load chart JSON for relevant plots
    relevant_plots = select_visualizations(last_question, state.get('model'), state.get('api_key'))
    
    chart_json = []
    if relevant_plots and relevant_plots.get('paths'):                                    # Check if dict exists AND paths is not empty 
        for path in relevant_plots['paths']:
            chart_json.append(load_chart_json(path))

    LOGGER.info("Data exploration completed successfully.")
    LOGGER.info("=" * 40)

    return {
        'response': [AIMessage(content=result.content)],
        'sql_query': query_response.content,
        'chart_json': chart_json if chart_json else None
    }

def EmailWriter_node(state: State):
    """
    Description: Generate marketing email content based on analysis.
    Args:
        state (State): The current state of the workflow.
    Return:
        dict: A dictionary containing the generated email content.
    """

    data_manager = state.get('data_manager')
    leads_scored = data_manager.leads
    transactions = data_manager.transactions
    products = data_manager.products

    last_message = state.get('message', [])[-1] if state.get('message') else None       # Get the last user message for email generation

    models = get_models(state.get('api_key'))
    llm = models[state.get('model')]
    prompt_template = ChatPromptTemplate.from_template(BEST_EMAILS_PROMPT)
    agent = prompt_template | llm
    query = agent.invoke({'user_message': last_message.content})

    LOGGER.info(f"Query generated to detect target emails. \n {query.content}")

    target_emails = duckdb.query(query.content).to_df()
    prompt_template = ChatPromptTemplate.from_template(WRITE_EMAILS_PROMPT)
    agent = prompt_template | llm

    result = agent.invoke({
        'user_message': last_message.content,
        'target_emails': target_emails.to_json()
    })

    LOGGER.info("Email writer completed successfully.")
    LOGGER.info("=" * 40)

    return {'response': [AIMessage(content=result.content)],
            'sql_query': query.content}


def BusinessAnalyst_node(state: State):
    """
    Description: Explore and provide business metrics summary.
    Args:
        state (State): The current state of the workflow.
    Return:
        dict: A dictionary containing the business analysis response and chart JSON.
    """

    data_manager = state.get('data_manager')
    leads_scored = data_manager.leads
    transactions = data_manager.transactions
    products = data_manager.products

    # Merge transactions with products to get pricing
    transactions_with_price = transactions.merge(products[['product_id', 'suggested_price', 'description']], on='product_id', how='left')
    
    # Calculate basic metrics
    total_customers = int(leads_scored['user_email'].nunique())
    active_customers = int(transactions['user_email'].nunique())
    total_transactions = int(transactions.shape[0])
    total_revenue = float(transactions_with_price['suggested_price'].sum())
    
    # Top products by revenue - properly aggregate with specific column
    top_products = (transactions_with_price.groupby(['product_id', 'description']).agg({'suggested_price': ['sum', 'count']}).reset_index())
    top_products.columns = ['product_id', 'description', 'total_revenue', 'purchase_count']
    top_products = top_products.nlargest(5, 'total_revenue')
    
    # Top countries by revenue - use charge_country from transactions
    top_countries = (transactions_with_price.groupby('charge_country').agg({'suggested_price': ['sum', 'count']}).reset_index())
    top_countries.columns = ['charge_country', 'total_revenue', 'purchase_count']
    top_countries = top_countries.nlargest(5, 'total_revenue')

    business_summary = {
        'total_customers': total_customers,
        'total_transactions': total_transactions,
        'total_revenue': round(total_revenue, 2),
        'conversion_rate': round((active_customers / total_customers) * 100, 2),
        'avg_customer_value': round(total_revenue / total_customers, 2),
        'avg_transaction_value': round(total_revenue / total_transactions, 2),
        'min_transaction': round(float(transactions_with_price['suggested_price'].min()), 2),
        'max_transaction': round(float(transactions_with_price['suggested_price'].max()), 2),
        'active_customers': active_customers,
        'dormant_customers': total_customers - active_customers,
        'top_products': top_products.to_dict(orient='records'),
        'top_countries': top_countries.to_dict(orient='records'),
    }

    models = get_models(state.get('api_key'))
    llm = models[state.get('model')] 
    prompt_template = ChatPromptTemplate.from_template(BUSINESS_ANALYST_PROMPT)
    agent = prompt_template | llm

    messages = state.get('message', [])
    last_question = messages[-1].content if messages else "Provide comprehensive data analysis"

    # Invoke with all the data the prompt expects
    result = agent.invoke({
        'initial_question': last_question,
        'business_summary': business_summary
    })

    # Load chart JSON for relevant plots
    relevant_plots = select_visualizations(last_question, state.get('model'), state.get('api_key'))
    
    chart_json = []
    if relevant_plots and relevant_plots.get('paths'):
        for path in relevant_plots['paths']:
            chart_json.append(load_chart_json(path))

    LOGGER.info("Business analysis completed successfully.")
    LOGGER.info("=" * 40)

    # result is now an AIMessage object, extract content
    return {
        'response': [AIMessage(content=result.content)],
        'chart_json': chart_json if chart_json else None
    }

def MarketingAnalyst_node(state: State):
    """
    Description: Analyze customer segments using cached data from DataManager.
    Args:
        state (State): The current state of the workflow.
    Return:
        dict: A dictionary containing the marketing analysis response and chart JSON.
    """ 

    data_manager = state.get('data_manager')
    
    models = get_models(state.get('api_key'))
    llm = models[state.get('model')] 
    prompt_template = ChatPromptTemplate.from_template(MARKETING_ANALYST_PROMPT)
    agent = prompt_template | llm 

    try:
        leads_scored = data_manager.leads
        transactions = data_manager.transactions
        # Select only needed columns for analysis
        leads_scored = leads_scored[['user_email', 'p1', 'member_rating', 'customer_segment']]
        transactions = transactions[['user_email', 'purchased_at']]
    except Exception as e:
        LOGGER.error(f"Error loading data: {e}")
        return state

    # Calculate transaction_frequency (group by user_email and count transactions)
    purchase_frequency = transactions.groupby('user_email').size().reset_index(name='purchase_frequency')
    LOGGER.info(f"Transaction frequency calculated. Mean frequency: {purchase_frequency['purchase_frequency'].mean():.2f}")

    # Combines customer profiles with their purchase activity, keeping all customers even if they never purchased anything.
    df_analysis = leads_scored.merge(purchase_frequency, on='user_email', how='left')
    LOGGER.info(f"Features merged. Customer data shape: {df_analysis.shape}")

    # Fill missing values
    df_analysis['purchase_frequency'] = df_analysis['purchase_frequency'].fillna(0)

    # Create summary statistics for each customer segment and rename user_email to customer_count
    df_summary = df_analysis.groupby('customer_segment').agg({
        'p1': 'mean',                                                                                                           # Use mean for lead score                        
        'member_rating': 'mean',                                                                                                # Use mean for member rating                                                         
        'purchase_frequency': 'mean',                                                                                           # Use mean for purchase frequency      
        'user_email': 'count'                                                                                                   # Count customers in each segment   
    }).rename(columns={'user_email': 'customer_count'}).reset_index()

    # Round statistics for better readability
    df_summary['avg_p1'] = df_summary['p1'].round(3)
    df_summary['avg_member_rating'] = df_summary['member_rating'].round(2)
    df_summary['avg_purchase_frequency'] = df_summary['purchase_frequency'].round(2)

    # Convert summary statistics to JSON format
    segment_stats_json = df_summary[['customer_segment', 'customer_count', 
                                     'avg_p1', 'avg_member_rating', 'avg_purchase_frequency']].to_json(orient='records')

    
    messages = state.get('message', [])
    last_question = messages[-1].content if messages else ""
    result = agent.invoke({'initial_question': last_question, 
                           'segment_statistics': segment_stats_json})

    # Get the plot path safely
    plot_info = PlotGenerator().get_plot_by_title('Customer Segment Analysis')
    if plot_info and os.path.exists(plot_info['path']):
        chart_json = load_chart_json(plot_info['path'])
    else:
        chart_json = None
        LOGGER.warning("Chart JSON not found.")

    LOGGER.info("Marketing analysis completed successfully.")
    LOGGER.info("=" * 40)

    return {
        'response': [AIMessage(content=result.content)],
        'chart_json': [chart_json]
    }
# --------------------------------------GRAPH----------------------------------------------

builder = StateGraph(State)
builder.add_node('router', router_node)
builder.add_node('data_overview', DataOverview_node)
builder.add_node('data_exploration', DataExplorer_node)
builder.add_node('email_writer', EmailWriter_node)
builder.add_node('business_analysis', BusinessAnalyst_node)
builder.add_node('marketing_analysis', MarketingAnalyst_node)

builder.add_edge(START, 'router')
builder.add_conditional_edges('router', route_after_router, ['data_overview', 'data_exploration', 'email_writer',
                                                             'business_analysis', 'marketing_analysis'])
builder.add_edge('data_overview', END)
builder.add_edge('data_exploration', END)
builder.add_edge('email_writer', END)
builder.add_edge('business_analysis', END)
builder.add_edge('marketing_analysis', END)

graph = builder.compile()

# ---------------------------------------PLOTTING------------------------------------------

if not os.path.exists(marketing_path):
    try:
        # Try to generate the graph with Mermaid API with higher retry settings
        LOGGER.info("Attempting to generate marketing graph using Mermaid API...")
        #analyst_graph = graph.get_graph().draw_mermaid_png(max_retries=5, retry_delay=2.0)
        analyst_graph = graph.get_graph().print_ascii()                                                                         # Temporary change for testing without Mermaid API
        with open(marketing_path, 'wb') as f:
            f.write(analyst_graph)
        LOGGER.info("Marketing graph generated successfully using Mermaid API.")
    except Exception as e:
        LOGGER.warning(f"Mermaid API failed: {e}")
        LOGGER.info("Continuing without graph visualization. The application will work normally.")

# --------------------------------------CLASS----------------------------------------------

class MarketingAnalyst:
    """A Marketing Analyst agent that analyzes customer segments and provides insights."""
    
    def __init__(self, model=None, api_key=None, db_path='data/leads_scored.db'):
        """Initialize the Marketing Analyst agent.
        
        Args:
            model: Model name string (e.g., 'gpt-5-nano', 'llama3.1') or None for default
            api_key: OpenAI API key for session isolation in multi-user deployments
            db_path: Path to the database
        """
        self.model = model
        self.api_key = api_key
        self.db_path = db_path 
        self.compiled_graph = graph
        self.data_manager = DataManager()
        self.plot_generator = PlotGenerator()
        self.data_manager.load_data(db_path=self.db_path)
        self.plot_generator.generate_plots(self.data_manager)
        self.response = None
    
    def invoke_agent(self, user_instructions: str):
        """Invoke the agent with user instructions.
        
        Args:graph
            user_instructions: The user's question or request
        """
        messages = [HumanMessage(content=user_instructions)]
        # Pass the LLM instance through the state
        self.response = self.compiled_graph.invoke({
            'message': messages,
            'model': self.model,
            'api_key': self.api_key,
            'data_manager': self.data_manager
        })
        return self.response
    
    def get_response(self):
        """Get the last response from the agent.
        
        Returns:
            dict: Response containing insights, chart_json, summary_table, etc.
        """
        if self.response is None:
            raise ValueError("No response available. Call invoke_agent() first.")
        return self.response

# -------------------------------------------------------------------------------------










