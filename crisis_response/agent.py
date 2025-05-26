import os
import logging
from dotenv import load_dotenv

from google.adk.agents import Agent
from google.adk.tools.retrieval.vertex_ai_rag_retrieval import VertexAiRagRetrieval
from google.adk.tools import google_search
from vertexai.preview import rag  # Needed for RagResource
from google.adk.tools import agent_tool

from .prompts import CRISIS_RESPONSE_SYSTEM_INSTRUCTION

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.0-flash")  # Default if not set
RAG_CORPUS = os.getenv("RAG_CORPUS")

# --- Tool Definition ---

# Define the RAG tool
crisis_rag_retrieval = None
if RAG_CORPUS:
    logger.info(f"Initializing RAG tool with corpus: {RAG_CORPUS}")
    crisis_rag_retrieval = VertexAiRagRetrieval(
        name="retrieve_crisis_information",  # Descriptive name for the tool
        description=(
            "Use this tool to retrieve information from the curated crisis knowledge base (official documents, guidelines, etc.). "
            "Use for general procedures, safety tips, and established information."
        ),
        rag_resources=[
            rag.RagResource(
                rag_corpus=RAG_CORPUS
                # Optional: Add rag_corpora or google_search_engine_id here if needed
            )
        ],
        # Optional: Configure retrieval parameters
        # similarity_top_k=3,
        # vector_distance_threshold=0.5
    )
else:
    logger.warning(
        "RAG_CORPUS environment variable not set. RAG tool will not be available."
        " The agent will rely solely on Google Search and its internal knowledge."
    )

# Google Search tool is wrapped in its own agent below.

# --- Agent Definition ---

search_agent = Agent(
    model=MODEL_NAME,
    name="GoogleSearch",
    instruction="""
You are an advanced AI, operating as an elite Google Search specialist. Your sole mission is to provide precise, real-time information on crisis situations directly and immediately in response to user requests.

Your Internal Mandate (Execute this process internally with maximum speed and precision; DO NOT describe these steps in your response to the user):

Instantaneous Request Analysis: Upon receiving a user query, immediately dissect it to identify the core components: specific crisis type (e.g., earthquake, wildfire, industrial accident), precise geographic location, and the exact nature of information required (e.g., current status, official advisories, affected zones, casualty reports, humanitarian efforts).

Optimized Search Simulation & Source Prioritization: Internally simulate an optimal Google Search strategy. This includes deploying advanced search operators and real-time filters. Critically prioritize data from the most authoritative and timely sources, such as official government emergency agencies (e.g., FEMA, CalOES, WHO), established international news organizations with strong verification records, and credible non-governmental organizations (NGOs) directly involved.

Rapid Verification & Cross-Referencing: Swiftly evaluate the gathered information for its timeliness, accuracy, and relevance. Internally cross-reference critical details across multiple high-credibility sources to ensure reliability before relaying.

Direct Information Synthesis: Consolidate the verified, most crucial information into a concise, clear, and directly actionable update tailored to the user's query.

Your Output to the User:
Your response must be immediate and consist only of the synthesized real-time information relevant to the crisis. Do not explain your search process, your source evaluation, or your synthesis steps. Begin your response directly with the information. 
Provide answer to the question asked instead of providing unnecessary details.

    """,
    tools=[google_search],
)

# List of tools for the agent
agent_tools = []
if crisis_rag_retrieval:
    agent_tools.append(
        agent_tool.AgentTool(agent=crisis_rag_retrieval)
    )
agent_tools.append(
    agent_tool.AgentTool(agent=search_agent)
)


logger.info(f"Initializing Crisis Response Agent with model: {MODEL_NAME}")
# Adjust logging to handle both tool instances and string names
logger.info(
    f"Tools configured: {[t.name if hasattr(t, 'name') else t for t in agent_tools]}"
)


# Instantiate the agent using the base Agent class
# The ADK runner will use this 'root_agent' instance.
root_agent = Agent(
    model=MODEL_NAME,
    instruction=CRISIS_RESPONSE_SYSTEM_INSTRUCTION,
    tools=agent_tools,
    name="crisis_response_agent",  # Add required name parameter
    description="Provides information and assistance during crisis situations.",  # Optional but good practice
)

logger.info("Crisis Response Agent initialized successfully.")
