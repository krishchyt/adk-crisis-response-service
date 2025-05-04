# Crisis Response Information Agent

## Overview

This agent is designed to provide verified information and resources during a crisis (e.g., natural disaster, pandemic). It utilizes Retrieval-Augmented Generation (RAG) with the Vertex AI RAG Engine to fetch information from a curated corpus of crisis documents, and uses Google Search for real-time updates and location-specific information.

## Agent Details
| Attribute         | Details                                                                |
| :---------------- | :--------------------------------------------------------------------- |
| **Interaction Type** | Conversational                                                       |
| **Complexity** | Intermediate                                                           |
| **Agent Type** | Single Agent                                                           |
| **Components** | Vertex AI RAG Engine, Google Search                                     |
| **Vertical** | Social Good, Emergency Response                                        |

## Setup and Installation

### Prerequisites

*   A Google Cloud Project with Vertex AI API and Cloud Storage API enabled.
*   `gcloud` CLI installed and authenticated (`gcloud auth application-default login`).
*   Python >=3.11, <3.13 and Poetry (due to Vertex AI Agent Engine deployment requirements).
*   Environment variables set up (see `.env.example`). You will need `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, and a `STAGING_BUCKET` (a GCS bucket for deployment artifacts).

### Project Setup

1.   **Prerequisites**

* To begin with, please firstly _clone this repo_, then install the required packages with the poetry command below.

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install poetry
    ```
2.  **Navigate to this agent's directory:**
    ```bash
    cd adk-samples/crisis-response-service
    ```
3.  **Install Dependencies:**
    ```bash
    poetry install
    ```
4.  **Set up Environment Variables:**
    *   Copy `.env.example` to `.env`.
    *   Fill in your `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, and `STAGING_BUCKET`.
    *   Initially, leave `RAG_CORPUS` and `AGENT_ENGINE_ID` blank.
5.  **Prepare Crisis Corpus:**
    *   Modify `crisis_response/shared_libraries/prepare_crisis_corpus.py` to include URLs to your desired corpus documents in the `EXAMPLE_DOCUMENTS` list.
    *   Run the corpus preparation script:
        ```bash
        poetry run python crisis_response/shared_libraries/prepare_crisis_corpus.py
        ```
    *   **IMPORTANT**: After the first successful run, the script will create/update the `RAG_CORPUS` variable in your `.env` file with the RAG Corpus resource name. This is needed for the agent to find the corpus.

## Running the Agent Locally

1.  **Ensure your `.env` file is correctly configured, especially `RAG_CORPUS`.**
2.  **Run via ADK CLI:**
    ```bash
    # The ADK runner looks for 'root_agent' in the module specified in pyproject.toml ([tool.adk].module)
    poetry run adk run crisis_response
    ```
3.  **Run via ADK Web UI:**
    ```bash
    poetry run adk web
    ```
    Then select `crisis_response` from the dropdown in the web interface.

### Example Interaction

**User:** "What are the safety tips for an earthquake?"
**Agent:** (Responds with information from the RAG corpus, citing sources)

**User:** "Are there any active wildfire alerts in Dublin, California right now?"
**Agent:** (Uses Google Search, focusing on official sites like CalFire or inciweb, to provide current information)

**User:** "I'm in San Francisco, California. Where is the nearest Red Cross shelter?"
**Agent:** (Uses Google Search to find shelter information relevant to the location)


## Deploying the Agent to Vertex AI Agent Engine

1.  **Ensure your `.env` file has `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, and `STAGING_BUCKET` set.**
2.  **Run the deployment script:**
    ```bash
    poetry run python deployment/deploy.py --create
    ```
    > **Note**: This process could take more than 10 minutes to finish, please be patient.

3.  **IMPORTANT**: After a successful deployment, the script will update your `.env` file with the `AGENT_ENGINE_ID`. This ID can be used to interact with the deployed agent via the Vertex AI API or SDK.

When the deployment finishes, it will print a line like this:

```
Created remote agent: projects/<PROJECT_NUMBER>/locations/<PROJECT_LOCATION>/reasoningEngines/<AGENT_ENGINE_ID>
```

You may interact with the deployed agent programmatically in Python:

```python
import dotenv
import os
dotenv.load_dotenv()  # May skip if you have exported environment variables.
from vertexai import agent_engines

# Get the deployed agent engine ID from your .env file or the deployment output
agent_engine_id = os.getenv("AGENT_ENGINE_ID")
# Example query relevant to the agent
user_input = "What should I do during an earthquake?"

if not agent_engine_id:
    print("Error: AGENT_ENGINE_ID not found in environment variables.")
else:
    agent_engine = agent_engines.get(agent_engine_id)
    session = agent_engine.create_session(user_id="example_user") # Use a descriptive user_id
    print(f"Querying agent {agent_engine_id}...")
    for event in agent_engine.stream_query(
        user_id=session["user_id"], session_id=session["id"], message=user_input
    ):
        # Check if the event contains text content before printing
        if event and "content" in event and "parts" in event["content"]:
             for part in event["content"]["parts"]:
                 if "text" in part:
                     print(part["text"], end="") # Print parts as they stream
    print() # Add a newline at the end
```

To delete the deployed agent, you may run the following command:

```bash
python3 deployment/deploy.py --delete --agent_engine_id=${AGENT_ENGINE_ID}
```

## Customization

*   **Corpus:** The most important customization is expanding the `EXAMPLE_DOCUMENTS` list in `crisis_response/shared_libraries/prepare_crisis_corpus.py` with comprehensive and trusted crisis information documents (PDFs accessible via URL).
*   **Prompts:** Refine `crisis_response/prompts.py` to improve the agent's tone, accuracy, and decision-making for tool use.
*   **Tools:** For more advanced functionality, you could develop custom tools in `crisis_response/tools/` to interact with specific crisis APIs (e.g., FEMA API, NOAA API) if available and needed. Remember to add any new custom tools to the `agent_tools` list in `crisis_response/agent.py`.