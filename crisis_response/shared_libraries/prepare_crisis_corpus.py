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

from google.auth import default
import vertexai
from vertexai.preview import rag
import os
from dotenv import load_dotenv, set_key
import requests
import tempfile
from pathlib import Path


# Load environment variables from .env file
load_dotenv()

# --- Please fill in your configurations ---
# Retrieve the PROJECT_ID from the environmental variables.
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
if not PROJECT_ID:
    raise ValueError(
        "GOOGLE_CLOUD_PROJECT environment variable not set. Please set it in your .env file."
    )
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION")
if not LOCATION:
    raise ValueError(
        "GOOGLE_CLOUD_LOCATION environment variable not set. Please set it in your .env file."
    )

# Updated Corpus details
CORPUS_DISPLAY_NAME = os.getenv("RAG_CORPUS_DISPLAY_NAME", "Crisis_Response_Corpus")
CORPUS_DESCRIPTION = os.getenv(
    "RAG_CORPUS_DESCRIPTION", "Corpus for Crisis Response Information Agent"
)

# List of documents to add
EXAMPLE_DOCUMENTS = [
    {
        "url": "https://www.ready.gov/sites/default/files/2024-03/ready.gov_earthquake_hazard-info-sheet.pdf",
        "filename": "earthquake_info_sheet.pdf",
        "description": "FEMA Earthquake Information Sheet",
    },
    {
        "url": "https://www.who.int/docs/default-source/coronaviruse/coping-with-stress.pdf?sfvrsn=9845bc3a_2",
        "filename": "who_coping_with_stress.pdf",
        "description": "WHO Guide on Coping with Stress During Outbreaks",
    },
    # Add more documents here
]

ENV_FILE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", ".env")
)


# --- Start of the script ---


def initialize_vertex_ai():
    credentials, _ = default()
    vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)


def create_or_get_corpus():
    """Creates a new corpus or retrieves an existing one."""
    embedding_model_config = rag.EmbeddingModelConfig(
        publisher_model="publishers/google/models/text-embedding-004"
    )
    existing_corpora = rag.list_corpora()
    corpus = None
    for existing_corpus in existing_corpora:
        if existing_corpus.display_name == CORPUS_DISPLAY_NAME:
            corpus = existing_corpus
            print(f"Found existing corpus with display name '{CORPUS_DISPLAY_NAME}'")
            break
    if corpus is None:
        corpus = rag.create_corpus(
            display_name=CORPUS_DISPLAY_NAME,
            description=CORPUS_DESCRIPTION,
            embedding_model_config=embedding_model_config,
        )
        print(f"Created new corpus with display name '{CORPUS_DISPLAY_NAME}'")
    return corpus


def download_pdf_from_url(url, output_path):
    """Downloads a PDF file from the specified URL."""
    print(f"Downloading PDF from {url}...")
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Raise an exception for HTTP errors

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"PDF downloaded successfully to {output_path}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {url}: {e}")
        return False


def upload_pdf_to_corpus(corpus_name, pdf_path, display_name, description):
    """Uploads a PDF file to the specified corpus."""
    print(f"Uploading {display_name} to corpus...")
    try:
        # Check if file with the same display name already exists
        existing_files = rag.list_files(corpus_name=corpus_name)
        for existing_file in existing_files:
            if existing_file.display_name == display_name:
                print(
                    f"File '{display_name}' already exists in corpus. Skipping upload."
                )
                return existing_file  # Return existing file object

        # If not found, upload
        rag_file = rag.upload_file(
            corpus_name=corpus_name,
            path=pdf_path,
            display_name=display_name,
            description=description,
            # Optional: Add chunking strategy if needed
            # rag_file_chunking_config=rag.RagFileChunkingConfig(chunk_size=512, chunk_overlap=100)
        )
        print(f"Successfully uploaded {display_name} to corpus")
        return rag_file
    except Exception as e:
        print(f"Error uploading file {display_name}: {e}")
        return None


def update_env_file(corpus_name, env_file_path):
    """Updates the .env file with the corpus name."""
    try:
        # Check if the key already exists and has the correct value
        load_dotenv(
            dotenv_path=env_file_path, override=True
        )  # Reload to get current value
        current_value = os.getenv("RAG_CORPUS")
        if current_value != corpus_name:
            set_key(env_file_path, "RAG_CORPUS", corpus_name)
            print(f"Updated RAG_CORPUS in {env_file_path} to {corpus_name}")
        else:
            print(f"RAG_CORPUS in {env_file_path} is already set correctly.")
    except Exception as e:
        print(f"Error updating .env file: {e}")


def list_corpus_files(corpus_name):
    """Lists files in the specified corpus."""
    files = list(rag.list_files(corpus_name=corpus_name))
    print(f"\n--- Files currently in corpus: {corpus_name} ---")
    if not files:
        print("No files found.")
    else:
        print(f"Total files: {len(files)}")
        for file in files:
            print(f"- {file.display_name} (Name: {file.name})")
    print("--------------------------------------------------")


def main():
    initialize_vertex_ai()
    corpus = create_or_get_corpus()

    # Update the .env file with the corpus name (do this early)
    update_env_file(corpus.name, ENV_FILE_PATH)

    # Create a temporary directory to store the downloaded PDFs
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temporary directory: {temp_dir}")

        successful_uploads = 0
        for doc_info in EXAMPLE_DOCUMENTS:
            pdf_path = Path(temp_dir) / doc_info["filename"]
            download_successful = False

            # Download the PDF from the URL if URL exists
            if doc_info.get("url"):
                download_successful = download_pdf_from_url(doc_info["url"], pdf_path)
            else:
                # Handle case for local files if needed (assuming they are pre-placed)
                # local_source_path = Path(__file__).parent.parent / "data" / "corpus" / doc_info["filename"]
                # if local_source_path.exists():
                #    shutil.copy(local_source_path, pdf_path) # Copy to temp dir for upload
                #    download_successful = True # Treat as successful download
                # else:
                #    print(f"Local file {doc_info['filename']} not found. Skipping.")
                print(
                    f"No URL provided for {doc_info['filename']}. Assuming local file (logic not implemented). Skipping."
                )  # Placeholder

            # Upload the PDF to the corpus if download was successful
            if download_successful and pdf_path.exists():
                rag_file = upload_pdf_to_corpus(
                    corpus_name=corpus.name,
                    pdf_path=str(pdf_path),  # upload_file expects string path
                    display_name=doc_info["filename"],
                    description=doc_info["description"],
                )
                if rag_file:
                    successful_uploads += 1
            elif not doc_info.get("url"):
                pass  # Skip upload if no URL and local file logic isn't implemented/successful
            else:
                print(
                    f"Skipping upload for {doc_info['filename']} due to download failure or file not found."
                )

        print(
            f"\nFinished processing documents. Successful uploads: {successful_uploads}"
        )

    # List all files in the corpus at the end
    list_corpus_files(corpus_name=corpus.name)


if __name__ == "__main__":
    main()
