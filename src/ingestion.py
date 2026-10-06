## ingestion.py

"""Build and load a Chroma vector store from the tariff PDF for retrieval."""

import os
import re
from langchain_community.document_loaders import PyPDFLoader
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from src.config import TARIFF_DATA_PATH, CHROMA_DIR, EMBEDDING_MODEL_NAME

# Section headings like "1.1 LIGHT DUES" are treated as boundaries for chunking the
# tariff into semantically grouped documents.

COLLECTION_NAME = "tariff_sections_v3"
SECTION_HEADING_PATTERN = re.compile(r"(?m)^\s*(\d+(?:\.\d+)+)\s+([A-Z][A-Z /&'-]{3,})\s*$")

def _build_section_documents(pages, text_splitter):
    section_records = []
    current = None

    for page in pages:
        page_text = page.page_content or ""
        matches = list(SECTION_HEADING_PATTERN.finditer(page_text))
        cursor = 0
        for match in matches:
            if current is not None:
                current["text"] += page_text[cursor:match.start()]
                section_records.append(current)
            current = {
                "id": match.group(1),
                "name": match.group(2).strip(),
                "text": page_text[match.start():match.end()],
                "start_page": page.metadata.get("page"),
            }
            cursor = match.end()

        if current is not None:
            current["text"] += page_text[cursor:]

    if current is not None:
        section_records.append(current)

    documents = []
    for record in section_records:
        metadata = {
            "tariff_section_id": record["id"],
            "tariff_section_name": record["name"],
            "tariff_section_start_page": record["start_page"] or 0,
        }
        for chunk in text_splitter.create_documents([record["text"]], metadatas=[metadata]):
            documents.append(chunk)
    return documents

def initialize_vector_store():
    """Loads PDF document, splits it into semantic chunks, and builds/loads the Chroma vector store."""

    #embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL_NAME)
    if os.path.exists(CHROMA_DIR) and os.listdir(CHROMA_DIR):
        # Load existing vector store if available
        vector_store = Chroma(
            collection_name=COLLECTION_NAME,
            persist_directory=CHROMA_DIR,
            embedding_function=embeddings,
        )
        if vector_store._collection.count() > 0:
            metadata = vector_store.get(limit=1).get("metadatas", [{}])[0] or {}
            if "tariff_section_id" in metadata:
                return vector_store

            # A new collection avoids reusing a legacy wrapper with a deleted collection.

    if not os.path.exists(TARIFF_DATA_PATH):
        raise FileNotFoundError(f"Tariff PDF not found at {TARIFF_DATA_PATH}. Please add the file.")

    loader = PyPDFLoader(TARIFF_DATA_PATH)
    pages = loader.load()

    # Exclude first 8 pages 
    pages = pages[8:] # this needs to be a parameter, as the number of pages may change

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", " ", ""]
    )
    docs = _build_section_documents(pages, text_splitter)

    vector_store = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=CHROMA_DIR
    )
    return vector_store