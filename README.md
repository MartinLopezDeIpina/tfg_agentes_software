This repository contains the code developed for my bachelor's thesis at UPV/EHU. For detailed information about the methodology, evaluation, and findings, please refer to the complete thesis document (thesis_document.pdf). This README provides a project overview and deployment guide for the system.

## What did I do?

I developed a multi-agent system based on Large Language Models designed to assist new developers during software project onboarding by synthesizing information from multiple distributed sources.

## 🎯 Overview

This system addresses the information overload challenge that new developers face when joining software projects. Instead of manually searching through scattered documentation, code repositories, and management systems, developers can ask natural language questions and receive comprehensive answers with proper source citations.

## 🏗️ Architecture

The system consists of **5 specialized agents** that access different data sources:

- **Code Agent**: Analyzes source code repositories using RAG techniques
- **Documentation Agent**: Searches through project documentation
- **Confluence Agent**: Accesses design and style guides
- **GitLab Agent**: Retrieves project management information
- **Google Drive Agent**: Processes HTML mockups and additional resources

These agents are coordinated by:
- **Orchestrator Agent**: Determines which specialized agents to execute
- **Planner Agent**: Creates sequential execution plans for complex queries
- **Formatter Agent**: Structures responses with proper citations

## ✨ Key Features

- **Model Context Protocol (MCP)**: Standardized tool integration
- **Persistent Memory**: Learns from previous interactions
- **Adaptive Design**: Adjusts complexity based on query difficulty
- **Citation System**: Provides verifiable source references
- **Automated Evaluation**: Quantifiable performance metrics

## 📊 Automated Evaluation System

The system was evaluated using an **LLM-as-Judge approach** with automated quantifiable metrics implemented through LangSmith SDK. A ground truth dataset of **46 real-world questions** was created from requirements elicitation with LKS Next professionals, covering three complexity levels: single-source, multi-source, and sequential multi-source queries with dependencies.
### Used Metrics

- **🎯 LLM Judge Precision (80%+)**: Measures if responses adequately address questions by evaluating presence of essential annotated concepts
- **🔧 Tool Precision**: Evaluates correct tool selection combining necessary tools used vs. unnecessary tools avoided
- **🚫 Hallucination Precision**: Tests ability to abstain when lacking sufficient information on "impossible to answer" questions
- **📚 Citation Precision**: Validates accuracy of document references against annotated requirements
- **💰 Resource Usage**: Tracks token consumption, API costs, execution time and computational efficiency

## 🛠️ Tech Stack

- **LangChain**: Model management and prompting
- **LangGraph**: Agent orchestration and workflow
- **LangSmith**: Monitoring and evaluation
- **PostgreSQL + PGVector**: Vector database for RAG
- **Python**: Core implementation

## Deployment guide

Steps to deploy the system on a Linux machine. Tested only on Ubuntu 24.04. 

### Install PostgreSQL

The system uses a PostgreSQL database which needs to be installed locally:

```bash
sudo apt install postgresql
sudo -u postgres psql postgres
```

```sql
ALTER USER postgres WITH PASSWORD 'password';
```

```bash
sudo apt install postgresql-server-dev-16
```

Install PGVector on your machine following [GitHub instructions](https://github.com/pgvector/pgvector), then create the vector extension in the database:

```bash
cd /tmp
git clone --branch v0.8.0 https://github.com/pgvector/pgvector.git
cd pgvector
make
make install # may need sudo
```

```bash
sudo -u postgres psql postgres
CREATE EXTENSION vector;
```

### Install Python 3.12.3, UV and Node

Python 3.12.3 is required as it is the main programming language used:

```bash
sudo apt install python3.12-venv
```

Node is also used in the Google Drive MCP server. You can install it following the [official instructions](https://nodejs.org/en/download):

```bash
# Download and install nvm:
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash

# in lieu of restarting the shell
\. "$HOME/.nvm/nvm.sh"

# Download and install Node.js:
nvm install 22

# Verify the Node.js version:
node -v # Should print "v22.17.0".
nvm current # Should print "v22.17.0".

# Verify npm version:
npm -v # Should print "10.9.2".
```

UV package manager is also used in MCP servers. You may install it using the [official instructions](https://docs.astral.sh/uv/getting-started/installation/#standalone-installer) too:

```bash
curl -LsSf https://astral.sh/uv/install.sh | less
```

### Set up virtual environments

Clone the project using the GitHub URL. From now on, I will reference the project path where you cloned it as "$PPATH".

```bash
git clone https://github.com/MartinLopezDeIpina/tfg_agentes_software.git $PPATH
cd tfg_agentes_software/
python3 -m venv servidor_mcp_bd_codigo/.venv servidor_mcp_confluence/.venv sistema_agentes/.venv frontend/.venv
```

The project uses five independent environments for package management in the following subdirectories:

- servidor_mcp_bd_codigo: code MCP server
```bash
source servidor_mcp_bd_codigo/.venv/bin/activate
pip install -r servidor_mcp_bd_codigo/requirements.txt
```

- servidor_mcp_confluence: Confluence MCP server
```bash
source servidor_mcp_confluence/.venv/bin/activate
pip install -r servidor_mcp_confluence/requirements.txt
```

- servidor_mcp_google_drive: Google Drive MCP server
```bash
npm install servidor_mcp_google_drive/
```

- sistema_agentes: contains the agent system code
```bash
source sistema_agentes/.venv/bin/activate
pip install -r sistema_agentes/requirements.txt
```

- frontend: contains requirements to launch the Open WebUI Docker
```bash
source frontend/.venv/bin/activate
pip install -r frontend/requirements.txt
```

### Set up .env files

The project requires setting up the following .env files:

- servidor_mcp_bd_codigo/.env:
```bash
OPENAI_API_KEY=

LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=

DB_USER='postgres'
DB_PASSWORD=
DB_HOST='localhost'
DB_PORT='5432'
DB_NAME='postgres'

DIRECTORY_TO_INDEX="your/software/project/directory"
```

- servidor_mcp_confluence/.env:
```bash
CONFLUENCE_URL=
CONFLUENCE_USERNAME=
CONFLUENCE_TOKEN=
MCP_PORT=9000
```

- sistema_agentes/.env:
```bash
OPENAI_API_KEY=
MISTRAL_API_KEY=
HUGGINGFACEHUB_API_TOKEN=
GROQ_API_KEY=

LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=

MCP_CODE_SERVER_HOST=localhost
MCP_CODE_SERVER_PORT=8000

CONFLUENCE_HOST=localhost
CONFLUENCE_PORT=9000

GITLAB_PERSONAL_ACCESS_TOKEN=

GDRIVE_FOLDER_ID=

FILESYSTEM_DOCS_FOLDER="/wherever/the/software/project/is/located"

DB_USER=postgres
DB_PASSWORD=
DB_HOST=localhost
DB_PORT=5432
DB_NAME=postgres

# Random key
SECRET_KEY=sjiisafoisdjpgjqwepiojf98354758qopisdhf
```

### Set up Google Drive credentials

In order to set up the Google Drive MCP server, the servidor_mcp_google_drive/credentials/.gdrive-server-credentials.json file needs to be configured. It contains the access token credentials for the Google Cloud application managing the Google Drive access. In order to generate it, follow the [official Google Drive MCP steps](https://github.com/modelcontextprotocol/servers-archived/tree/main/src/gdrive).

Once the Google Cloud credentials have been established, execute the servidor_mcp_google_drive/.auth.sh script. It will request you to log into your Google account in your browser, which will generate the servidor_mcp_google_drive/credentials/.gdrive-server-credentials.json file. This token will grant access to the Google Drive API.

### Clone GitLab project

The original case study employed a project which required a VPN to be connected to access the GitLab repository. After making sure you can access the code repository, clone it to a local directory.

After cloning it, you may generate the external documentation using [repoagent](https://github.com/OpenBMB/RepoAgent). For this, install the pip package on your machine and execute the following command. Note that you need to set up your OPENAI_API_KEY as an environment variable first:

```bash
python3 -m venv ~/.venv
source ~/.venv/bin/activate
pip install repoagent
repoagent run --model gpt-4o-mini --target-repo-path /your/software/project/directory --markdown-docs-path /wherever/the/project/is/tfg_agentes_software/sistema_agentes/static/gen_docs/
```

The documentation must be generated in the gen_docs directory in order for the repo_chunker to find it.

### Index project embeddings

To index the software project's chunks in files, execute the main.py script in servidor_mcp_bd_codigo:

```bash
cd servidor_mcp_bd_codigo
source .venv/bin/activate
PYTHONPATH=$PPATH/tfg_agentes_software python3 -m servidor_mcp_bd_codigo.main
```

It will execute the following lines:
```python
# Create and store file chunks into PostgreSQL database
file_chunker = FileChunker(
	chunk_max_line_size=200,
	chunk_minimum_proportion=0.2
)
file_chunker.chunk_repo(DIRECTROY_TO_INDEX)


# Index chunks into embeddings with pgvector plugin
run_documentation_pipeline_sync(DIRECTROY_TO_INDEX, files_to_ignore)
```

Make sure to define the DIRECTORY_TO_INDEX variable in servidor_mcp_bd_codigo/.env

### Execute MCP servers

Run code MCP server:
```bash
source servidor_mcp_bd_codigo/.venv/bin/activate
PYTHONPATH=$PPATH/tfg_agentes_software/servidor_mcp_bd_codigo python3 -m src.mcp_code_server
```

Run Confluence MCP server:
```bash
source servidor_mcp_confluence/.venv/bin/activate
PYTHONPATH=$PPATH/tfg_agentes_software/servidor_mcp_confluence python3 -m servidor_mcp_confluence.launch_mcp_server_confluence
```

Log into your Google Drive account: 
```bash
cd servidor_mcp_google_drive/
./auth.sh
```
It will open the OAuth Google authenticator in your browser. You will have access to the Google Drive folder for 1 hour.

### Execute Open WebUI

Install Docker, then:
```bash
sudo frontend/script.sh
docker logs open-webui --tail 50 -f
```

Once executing, you will need to upload the sistema_agentes/src/web_app/openwebui_functions/sse_proxy_function.py as an Open WebUI function. For this, in the Open WebUI web interface, navigate to the following path and paste the file:
User → Admin panel → Functions → upload sistema_agentes/src/web_app/openwebui_functions/sse_proxy_function.py

Once uploaded, you also need to activate it using the interactive switch.

### Execute sistema_agentes

You can either run the script version:
```bash
source sistema_agentes/.venv/bin/activate
PYTHONPATH=$PPATH/tfg_agentes_software/sistema_agentes python3 -m sistema_agentes.main
```

Or the web version:
```bash
source sistema_agentes/.venv/bin/activate
PYTHONPATH=$PPATH/tfg_agentes_software/sistema_agentes python3 -m sistema_agentes.src.web_app.app
```
