## 🤖 Multi-Agent Marketing Platform for Business Intelligence, SQL Automation & Email Targeting

<p align="left">
  <img src="https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Streamlit-Deployment-26A5E4?logo=streamlit&logoColor=white" />
  <img src="https://img.shields.io/badge/LangChain-Agents-1F6FEB?logo=LangChain" />
  <img src="https://img.shields.io/badge/LangGraph-Workflow-1F6FEB?logo=Langgraph" />
  <img src="https://img.shields.io/badge/OpenAI-ChatGPT_5_Nano-6E56CF?logo=OpenAI" />
  <img src="https://img.shields.io/badge/duckdb-Relational Database-3A40FF?logo=duckdb&logoColor=white" />
  <img src="https://img.shields.io/badge/plotly-Visualization-005F73?logo=plotly&logoColor=white" />
</p>

This project was deployed in this [website][demo]. It demonstrates the **capabilities of Machine Learning and Artificial Intelligence in marketing analytics.** By using language models, we can generate SQL queries, analyze customer segments, and create targeted marketing strategies.

In detail, this multi-agent AI system implements the following specialized agents:

  - 📋 **Data Overview:** Provides **an introduction to the database** used in this project. Displays column names, data types, brief descriptions of each table, and visualizations to complement the analysis.
  - 🔍 **Data Exploration:** It a **SQL generator that translates natural language into database queries** and interprets insights automatically.
  - 💼 **Business Analysis:** Produces a **business report based on key metrics** such as revenue, average order value, and customer lifetime value (CLV).
  - 📧 **Email Marketing:** Identifies target customers and **creates personalized email campaigns.**
  - 📣 **Marketing Strategy:** Segments customers into clusters and **generates targeted marketing strategies for each group.**

The following demo shows the performance of the following agents; Data Exploration, Email Marketing, and Marketing Strategy.

<p align="center">
  <video
    src="https://github.com/user-attachments/assets/60fcc44f-3ac5-4367-8383-5b436f806943"
    controls
    muted
    playsinline
    loop
    width="720" 
    height="405">
  </video>
</p>

---

### 🧭 Core Architecture

The architecture of this project is based on **SQLite3, LangGraph, and Streamlit.** Data is stored in a relational SQLite3 database, and DuckDB is used to execute analytical queries on the database. LangGraph manages the workflow by representing it as a graph, allowing each agent to be activated or used based on the current state. The state stores relevant information for each agent, such as chat history, user inputs, boolean flags, and more. Streamlit is used to deploy interactive demos with minimal implementation overhead.

In detail, this project implements six distinct AI agents, each described below:

<p align="center">
<img width="600" height="400" alt="Marketing" src="https://github.com/user-attachments/assets/11838a7b-bdeb-4368-bcf2-043ce4031df8" />
</p>

- 🔀 **Router**: Commonly named as 'Supervisor'. When a user interacts with the app, the router examines the current state (including user input, chat history, and flags) and **determines which agent should handle the next step.**

- 📋 **Data Overview:** This agent introduces the database by presenting relevant information about its tables, including the first five samples, column names, data types, number of missing values, and column distributions. **Using this data, the agent generates a comprehensive report** to familiarize the user with the database.

- 🔍 **Data Exploration:** This agent translates natural language queries into SQL. It operates in three parts:

    - Part 1: Receives a full description of the database (tables, columns, relationships) and **generates a SQL query** based on the user's objective.
    - Part 2: **Executes the generated SQL query** using DuckDB to retrieve the requested data.
    - Part 3: **Produces a report** that answers the user's question and provides additional insights.
    
- 💼 **Business Analysis:** This agent **generates business reports using key metrics** from the database, such as revenue, average purchases per user and transaction, top five countries, top-selling products, total customers, and transactions. These metrics are provided to a language model to create the final report.
   
- 📧 **Email Marketing:** This agent **identifies target emails and writes email campaigns.** It consists of two parts:

    - Part 1: **Generates a SQL query to identify target emails** based on the user's requirements.
    - Part 2: Composes a **personalized email for the marketing campaign.**
    
- 📣 **Marketing Strategy:** This agent uses the **K-Means algorithm** to cluster customers with similar behaviors. **Each cluster or segment can then be targeted with personalized marketing campaigns,** as members of a cluster share similar characteristics and preferences.

---
### 🔑 APIs required

- 🧠 **OPENAI:** Runs the LLMs. (I allocated $5 for this project; current spend ~$0.78.) Create an API key at [OpenAI][openai_api].  
  Models in this project were selected for a good price/performance balance (prices as of **09/08/2025**):
  - **[gpt-5-nano][gpt5nano]** — Input/Output price: $0.05 / $0.40
  - **[gpt-4.1-nano][gpt41nano]** — Input/Output price: $0.10 / $0.40
  - **[gpt-4o-mini][gpt4omini]** — Input/Output price: $0.15 / $0.60

---
### 🚀 Setup & Installation

**Remember that you can use the project in this [website][demo].** However, if you can run this project on local, you must follow the next steps.

I highly recommend using **['uv'][uv]** as your Python package & project manager. It installs packages and creates virtual environments **much faster** than traditional `pip` workflows. 

**1. Clone the Repository:** Clone the project repository to your local machine and navigate into the directory.
```bash
git clone https://github.com/your-username/marketing-analyst.git
cd marketing-analyst
```

**2. Create and Activate a Virtual Environment:** It is highly recommended to use a virtual environment to manage dependencies.

Using uv (Recommended):

```bash
uv venv
source .venv/bin/activate  # On Windows, use: .venv\Scripts\activate
```
Using Python's built-in `venv`:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows, use: .venv\Scripts\activate
```

**3. Install Dependencies:** Install all the required Python packages using your preferred tool.

Using uv (Recommended):

```bash
uv pip install -r requirements.txt
```
Using pip:
```bash
pip install -r requirements.txt
```
**4. Run the Application:** You can now start the project from your virtual environment automatically.

Using standard python: 
```bash
streamlit run app.py
```

## 📂 Repository Structure

The project is organized into several key files, each with a specific objective:


```text
📁 Marketing-Analyst/
├── 📄 .gitignore                # Specifies which files and directories should be ignored by Git.
├── 🚀 app.py                    # Streamlit entry point that runs the multi-agent marketing platform.
├── 🤖 marketing_analyst.py      # Core logic orchestrating the multi-agent workflow (LangGraph-based).
├── 🧠 customer_segmentation.py  # Handles clustering (K-Means) and customer segmentation analytics.
├── 🗃️ data_manager.py           # Loads and preprocesses data from CSV/DuckDB for analysis and agents.
├── 📈 generate_plots.py         # Generates and saves analytical visualizations to the /plots directory.
├── 🧾 prompts.py                # Contains system prompts for each AI agent (SQL, marketing, business, email).
├── 💼 plots/                    # JSON-based visualizations of customer and business insights.
│   ├── segment_analysis.json
│   ├── revenue_by_segment.json
│   ├── best_selling_products.json
│   └── ...
├── 📊 marketing_graph.png       # Visual diagram of the multi-agent architecture and workflow.
├── 🧩 data/                     # Source datasets used by the app (leads, products, transactions, etc.).
│   ├── leads.csv
│   ├── products.csv
│   ├── transactions.csv
│   └── ...
├── 📝 requirements.txt          # Lists Python dependencies (Streamlit, LangGraph, OpenAI, DuckDB, etc.).
└── 📘 README.md                 # Project overview, demo link, agent descriptions, and setup instructions.
```

#
✍️ Author: Antonio Castañares Rodríguez

📌 This repository documents a key project in my AI learning path, focused on gaining a deep and practical understanding of agentic systems to solve business problems.

[demo]: https://marketing-analyst.streamlit.app/ 
