
Project Folder Structure
port_tariff_poc/
├__ .env
|── data/
│   └── port_tariff_book.pdf
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── ingestion.py
│   ├── extraction.py
│   ├── retriever.py
│   └── main.py
├── requirements.txt
└── README.md

# Port Tariff RAG & Calculation PoC

A local Python application designed to process the Transnet National Ports Authority (TNPA) Tariff Book, extract vessel and port details from natural language prompts, and retrieve exact fee structures for **light dues, port dues, towage dues, VTS dues, pilotage dues, and running of vessel lines**.

## Prerequisites
1. Install [Ollama](https://ollama.com/) locally.
2. Pull a local model (e.g., Llama 3):
   If uisng ollam:
   ollama pull llama3

   if using LM Studio
   - Start the serve
   - Load the model to the server
# connect to LM Studio server for LLM
model = ChatOpenAI(
    base_url="http://127.0.0.1:1234/v1",  # LM Studio server endpoint
    api_key="lm-studio",
    model="google/gemma-4-12b",  # Match the exact model name shown in LM Studio     meta-llama-3.1-8b-instruct
    temperature=0.1
)

## Installation
- Clone or set up the project folder structure.
- Install dependencies: pip install -r requirements.txt
- Place your target port tariff PDF inside the data/ directory and name it port_tariff_book.pdf.

## Running the PoC

Execute the main application pipeline: python -m src.main

## src files:

### 1. src/ingestion.py: 
   Document Ingestion and Chunking of Port Tariffs: Port tariff books are heavy on tables and hierarchical sections. Load and split your tariff PDF into context-aware chunks.
   Embed and Store Chunks in a Local Vector Database: using a local embedding model (sentence-transformers) and store the chunks locally using ChromaDB.
   - embeddings

### src/config.py: 
   contains varaibles values
   
### src/extraction.py
   Extract Vessel and Port Details from the User Prompt: using the local LLM with structured output parsing or a targeted prompt to extract essential variables (e.g., port name, vessel type, gross tonnage, service required) directly from natural language input.

### src/retriever.py
      Execute Retrieval-Augmented Generation (RAG): Combine the extracted user criteria with relevant clauses retrieved from the vector database, (using search_type="similarity") feeding both into the local LLM to generate a precise cost breakdown or procedural guide.

### src/main.py
   1. initialize_vector_store: src.ingestion
   2. PromptExtractor: src.extraction
   3. TariffRetriever: src.retriever 

## LLM Models

- LLM model "gemma4:12b" OpenAI via LM Studio
- Embedding Model: "qwen3-embedding:latest" via Ollama


## Evaluation/ test
- eval_dataset.json: contains 



Alternative Py Packages:
#from langchain_community.llms import Ollama -> from langchain_openai import ChatOpenAI
from langchain_community.embeddings import OllamaEmbeddings/ HuggingFaceEmbeddings -> from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import Chroma -> from langchain_chroma import Chroma