# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Deployment script for Crisis Response Agent."""

import logging
import os

from absl import app
from absl import flags
from dotenv import load_dotenv, set_key, unset_key
import vertexai # This is often an alias for google.cloud.aiplatform
from vertexai import agent_engines
from vertexai.preview.reasoning_engines import AdkApp

# Assuming your root_agent is correctly defined in this path
from crisis_response.agent import root_agent

# --- Logger Configuration ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Flag Definitions ---
FLAGS = flags.FLAGS
flags.DEFINE_string("project_id", None, "GCP project ID.")
flags.DEFINE_string("location", None, "GCP location for the agent.")
flags.DEFINE_string(
    "staging_bucket_name",
    None,
    "GCP Cloud Storage bucket name for staging (without gs:// prefix).",
)
flags.DEFINE_string(
    "agent_engine_id",
    None,
    "Existing Agent Engine resource ID (e.g., projects/.../agentEngines/...). Required for update/delete if not in .env.",
)
flags.DEFINE_string(
    "display_name", "Crisis Response Agent", "Display name for the agent."
)
flags.DEFINE_string(
    "description",
    "Agent providing crisis information using RAG and Search.",
    "Description for the agent.",
)

flags.DEFINE_bool("list", False, "List all deployed Agent Engines.")
flags.DEFINE_bool("create", False, "Creates a new Agent Engine.")
flags.DEFINE_bool("delete", False, "Deletes an existing Agent Engine.")
flags.DEFINE_bool("update", False, "Updates an existing Agent Engine.")

flags.mark_bool_flags_as_mutual_exclusive(["create", "delete", "list", "update"])

# --- Environment and .env File Configuration ---
load_dotenv(override=True)

ENV_FILE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", ".env")
)


def _get_config_value(flag_value: str | None, env_var_name: str, error_message: str):
    """Gets configuration value from flag or environment variable."""
    value = flag_value if flag_value is not None else os.getenv(env_var_name)
    if not value:
        logger.error(error_message)
        raise ValueError(error_message)
    return value


def _update_env_file(key: str, value: str | None):
    """Updates or removes a key in the .env file."""
    try:
        if not os.path.exists(ENV_FILE_PATH):
            with open(ENV_FILE_PATH, "w") as f:
                pass
            logger.info(f"Created .env file at: {ENV_FILE_PATH}")

        if value is not None:
            set_key(ENV_FILE_PATH, key, value)
            logger.info(f"Updated {key} in {ENV_FILE_PATH} to {value}")
        else:
            unset_key(ENV_FILE_PATH, key) # Requires python-dotenv 0.21.0 or newer for unset_key
            logger.info(f"Removed {key} from {ENV_FILE_PATH}")
    except Exception as e:
        logger.error(f"Error updating .env file at {ENV_FILE_PATH}: {e}")


def _get_adk_app():
    """Prepares the AdkApp for deployment or update."""
    logger.info("Preparing ADK App...")
    return AdkApp(
        agent=root_agent,
        enable_tracing=True,
    )

DEPLOYMENT_REQUIREMENTS = [
    "google-adk>=0.1.0",
    "python-dotenv>=1.0.0", # Ensure unset_key is supported if you use it (0.21.0+)
    "google-cloud-aiplatform[adk,agent_engines]>=1.88.0",
    "google-cloud-storage>=2.10.0",
    "google-api-python-client>=2.88.0",
    "requests>=2.31.0",
    "llama-index>=0.12.0",
    "absl-py>=1.4.0", # Added for flags
]
EXTRA_PACKAGES = ["./crisis_response"]


def create_agent(current_location: str, current_staging_bucket_gs_path: str):
    """Creates a new Agent Engine for the Crisis Response Agent."""
    adk_app_instance = _get_adk_app()
    # Use passed-in, resolved values for logging
    logger.info(f"Deploying new agent to Vertex AI Agent Engine in {current_location}...")
    logger.info(f"Using staging bucket: {current_staging_bucket_gs_path}")
    logger.info(f"Requirements: {DEPLOYMENT_REQUIREMENTS}")
    logger.info(f"Extra packages: {EXTRA_PACKAGES}")

    try:
        remote_app = agent_engines.create(
            adk_app_instance,
            display_name=FLAGS.display_name,
            description=FLAGS.description,
            requirements=DEPLOYMENT_REQUIREMENTS,
            extra_packages=EXTRA_PACKAGES,
        )
        logger.info("Deployed agent to Vertex AI Agent Engine successfully!")
        logger.info(f"Resource name: {remote_app.resource_name}")
        _update_env_file("AGENT_ENGINE_ID", remote_app.resource_name)
        _update_env_file("AGENT_DISPLAY_NAME", FLAGS.display_name)
    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        exit(1)


def delete_agent(agent_engine_resource_id: str):
    """Deletes an existing Agent Engine."""
    if not agent_engine_resource_id:
        logger.error(
            "Agent Engine resource ID is required for deletion. "
            "Provide --agent_engine_id flag or ensure AGENT_ENGINE_ID is in .env."
        )
        exit(1)
    logger.info(f"Attempting to delete Agent Engine: {agent_engine_resource_id}")
    try:
        remote_agent = agent_engines.get(agent_engine_resource_id)
        remote_agent.delete(force=True)
        logger.info(f"Successfully deleted Agent Engine: {agent_engine_resource_id}")
        if agent_engine_resource_id == os.getenv("AGENT_ENGINE_ID"):
            _update_env_file("AGENT_ENGINE_ID", None)
            _update_env_file("AGENT_DISPLAY_NAME", None)
    except Exception as e:
        logger.error(f"Failed to delete Agent Engine {agent_engine_resource_id}: {e}")
        exit(1)


def list_all_agents(current_project_id: str, current_location: str):
    """Lists all deployed Agent Engines in the project and location."""
    # Use passed-in, resolved values for logging
    logger.info(f"Listing all Agent Engines in project {current_project_id} "
                f"location {current_location}...")
    try:
        remote_agents = agent_engines.list()
        if not remote_agents:
            print("No Agent Engines found.")
            return

        template = """
    -----------------------------------------
    Resource Name: {agent.name}
    Display Name: "{agent.display_name}"
    Create Time: {agent.create_time}
    Update Time: {agent.update_time}
    Description: {agent.description}
    -----------------------------------------"""
        remote_agents_string = "\n".join(
            template.format(agent=agent) for agent in remote_agents
        )
        print(f"Found Agent Engines:\n{remote_agents_string}")
    except Exception as e:
        logger.error(f"Failed to list Agent Engines: {e}")
        exit(1)

def update_agent(agent_engine_resource_id: str):
    """Updates an existing Agent Engine."""
    if not agent_engine_resource_id:
        logger.error(
            "Agent Engine resource ID is required for update. "
            "Provide --agent_engine_id flag or ensure AGENT_ENGINE_ID is in .env."
        )
        exit(1)

    adk_app_instance = _get_adk_app()
    logger.info(f"Attempting to update Agent Engine: {agent_engine_resource_id}")
    logger.info(f"New Display Name: {FLAGS.display_name}")
    logger.info(f"New Description: {FLAGS.description}")
    logger.info(f"Requirements: {DEPLOYMENT_REQUIREMENTS}")
    logger.info(f"Extra packages: {EXTRA_PACKAGES}")

    try:
        updated_agent = agent_engines.update(
            resource_name=agent_engine_resource_id,
            adk_app_source=adk_app_instance,
            display_name=FLAGS.display_name,
            description=FLAGS.description,
            requirements=DEPLOYMENT_REQUIREMENTS,
            extra_packages=EXTRA_PACKAGES,
        )
        logger.info(f"Successfully updated Agent Engine: {updated_agent.resource_name}")
        if agent_engine_resource_id == os.getenv("AGENT_ENGINE_ID") or not os.getenv("AGENT_ENGINE_ID"):
             _update_env_file("AGENT_ENGINE_ID", updated_agent.resource_name)
             _update_env_file("AGENT_DISPLAY_NAME", FLAGS.display_name)

    except Exception as e:
        logger.error(f"Failed to update Agent Engine {agent_engine_resource_id}: {e}")
        exit(1)


def main(argv: list[str]) -> None:
    del argv

    try:
        # These are the definitive values for the current script run
        current_project_id = _get_config_value(
            FLAGS.project_id,
            "GOOGLE_CLOUD_PROJECT",
            "Error: GOOGLE_CLOUD_PROJECT must be set via flag --project_id or environment variable.",
        )
        current_location = _get_config_value(
            FLAGS.location,
            "GOOGLE_CLOUD_LOCATION",
            "Error: GOOGLE_CLOUD_LOCATION must be set via flag --location or environment variable.",
        )
        current_staging_bucket_name = _get_config_value(
            FLAGS.staging_bucket_name,
            "STAGING_BUCKET_NAME",
            "Error: Staging bucket name must be set via flag --staging_bucket_name or STAGING_BUCKET_NAME in .env.",
        )
    except ValueError:
        exit(1)

    current_staging_bucket_gs_path = f"gs://{current_staging_bucket_name}"

    logger.info(f"Using Project ID: {current_project_id}")
    logger.info(f"Using Location: {current_location}")
    logger.info(f"Using Staging Bucket: {current_staging_bucket_gs_path}")

    vertexai.init(
        project=current_project_id,
        location=current_location,
        staging_bucket=current_staging_bucket_gs_path,
    )

    agent_id_from_flag_or_env = FLAGS.agent_engine_id if FLAGS.agent_engine_id else os.getenv("AGENT_ENGINE_ID")

    if FLAGS.list:
        list_all_agents(current_project_id, current_location) # Pass resolved values
    elif FLAGS.create:
        create_agent(current_location, current_staging_bucket_gs_path) # Pass resolved values
    elif FLAGS.delete:
        if not agent_id_from_flag_or_env:
            logger.error("Error: --agent_engine_id flag or AGENT_ENGINE_ID in .env is required for delete operation.")
            exit(1)
        delete_agent(agent_id_from_flag_or_env)
    elif FLAGS.update:
        if not agent_id_from_flag_or_env:
            logger.error("Error: --agent_engine_id flag or AGENT_ENGINE_ID in .env is required for update operation.")
            exit(1)
        update_agent(agent_id_from_flag_or_env)
    else:
        logger.info(
            "No action specified. Use --create, --delete, --update, or --list."
        )
        print("\nHelp: python your_script_name.py --help")


if __name__ == "__main__":
    # You might choose to make these flags required if they aren't found in the .env
    # flags.mark_flags_as_required(["project_id", "location", "staging_bucket_name"])
    # However, the current _get_config_value handles missing values by raising an error.
    app.run(main)