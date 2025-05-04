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