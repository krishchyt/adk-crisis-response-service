from .agent import root_agent  # Import the agent instance
from . import prompts  # Ensure prompts can be imported if needed elsewhere

# This makes `from crisis_response import root_agent` work.
__all__ = ["root_agent", "prompts"]  # Export the agent instance
