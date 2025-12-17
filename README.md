# Developer Dependency Agent

A local, AI-powered assistant that helps developers manage dependency security. It scans `requirements.txt` files, identifies vulnerabilities using OSV and PyPI data, and uses a local LLM (via Ollama) to provide actionable advice and remediation plans.

## Features

-   **Dependency Scanning**: Analyzes `requirements.txt` for known vulnerabilities (OSV database).
-   **Security Audits**: Integrates `pip-audit` for severity assessments.
-   **AI Advisory**: Uses local LLMs (Phi-3 or Llama-3) to reason about dependency constraints and suggest upgrades.
-   **Interactive UI**: Streamlit-based chat interface for easy interaction.
-   **Notebook Demo**: Jupyter notebook showcasing sample prompts and agent capabilities.
-   **Guardrails**: Built-in security guardrails to prevent prompt injection and keep the agent focused on dependency tasks.

## Prerequisites

-   **Python 3.8+**
-   **Ollama**: For running the local LLM. [Download Ollama](https://ollama.com/).

## Setup

1.  **Clone the repository** (if you haven't already):
    ```bash
    git clone <repository_url>
    cd Developer_Dependency_Agent
    ```

2.  **Create and activate a virtual environment**:
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Setup Ollama**:
    -   Ensure Ollama is installed and running.
    -   Pull the default model (`phi3`):
        ```bash
        ollama pull phi3
        ```
    -   (Optional) If you prefer Llama 3, pull it and set the environment variable:
        ```bash
        ollama pull llama3
        export PHI_MODEL=llama3  # Or configure in src/llm/client.py
        ```

## Usage

### Running the Web Interface

Start the Streamlit chat application:

```bash
streamlit run app/main.py
```

This will open a local web server (usually at `http://localhost:8501`) where you can:
-   Select your LLM provider.
-   Upload or paste requirements files.
-   Ask questions like "Analyze this file for vulnerabilities" or "How do I fix the conflict in flask?"

### Running the Demo Notebook

To explore the agent's capabilities programmatically and see sample outputs:

1.  **Launch Jupyter Notebook**:
    ```bash
    jupyter notebook
    ```

2.  **Open the Demo**:
    -   Navigate to `docs/demo_notebook.ipynb` in the Jupyter interface.
    -   Run the cells to see examples of:
        -   Vulnerability scanning on `samples/requirements_vulns.txt`.
        -   Handling malformed requirements (`samples/requirements_bad.txt`).
        -   Prompt injection defense mechanisms.

    *Note: The notebook is pre-configured to handle path resolution relative to the `docs/` directory.*

## Project Structure

-   `app/`: Streamlit application code.
-   `src/`: Core logic (Agents, Tools, LLM Client, Security).
-   `docs/`: Documentation and demo notebooks.
-   `samples/`: Sample `requirements.txt` files for testing.
-   `scripts/`: Utility scripts (e.g., proposal parsing).
