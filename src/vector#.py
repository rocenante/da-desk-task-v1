"""Build a simple vector index from tabular specification data for experimentation."""

# embedding text and convert to vector
import os
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
import pandas as pd

# This script creates a persistent document store using a local embedding model.

from src.config import TARIFF_DATA_PATH, CHROMA_DIR, EMBEDDING_MODEL_NAME, VESSEL_DATA_PATH


# read the ndmo specifications csv file
df = pd.read_csv(TARIFF_DATA_PATH)                              ## "data/ndmo_specifications.csv"

embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL_NAME)       ## "qwen3-embedding"

# the location where the vector database will be stored
db_location = CHROMA_DIR                                        ## "./vector_db"

# check if the vector database is already exist, if not create it and add documents
add_documents = not os.path.exists(db_location)

if add_documents:
    # create a list of Document objects from the dataframe
    # prepare the data in documents
    documents = []
    ids = []
    for i, row in df.iterrows():
        #documents.append(Document(page_content=str(content), metadata=content))
        document = Document(
            page_content=row["Specification Name"] + " " + row["Specification"],     # will be used in the query, what will be vectorised
            metadata={"Domain": row["Domain"], "Control": row["Control"]},           # additional data will not be used in the query but can be used for filtering
            id=str(i)
        )
        ids.append(str(i))
        documents.append(document)

# Initialize the vector store whether it is being created or loaded.
vector_store = Chroma(
        collection_name="ndmo_specifications",
        persist_directory=db_location, # store permanently in the specified directory.     # make the vector store persistent by saving it to disk
        embedding_function=embeddings  # pass embedding function to convert text to vector
)

if add_documents:
    # add the documents to the vector store
    vector_store.add_documents(documents, ids=ids)  # specify the documents to be added and corresponding ids

# make the vectors usable by the LLM
retriever = vector_store.as_retriever(search_kwargs={"k": 3})
