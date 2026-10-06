"""Legacy entry point for the local tariff RAG flow using the Ollama prompt template."""

## src/main.py
from pathlib import Path

from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

# from src.config import OLLAMA_MODEL
from src.ingestion import initialize_vector_store
from src.extraction import PromptExtractor
from src.retriever import TariffRetriever
from src.vessel import vessel_profile


def render_markdown_output(
    user_query: str,
    extracted_entities: dict,
    context: str,
    response: object,
) -> str:
    """Render a complete tariff pipeline result as human-readable Markdown."""
    response_text = getattr(response, "content", response)
    entity_lines = [
        f"- **{key}**: {value}" for key, value in sorted(extracted_entities.items())
    ]

    return "\n".join(
        [
            "# Tariff Calculation Output",
            "",
            "## User Query",
            "",
            user_query,
            "",
            "## Extracted Entities",
            "",
            *entity_lines,
            "",
            "## Relevant Tariff Context",
            "",
            context,
            "",
            "## Model Response",
            "",
            str(response_text).strip(),
            "",
        ]
    )


def run_pipeline(user_query: str, output_path: str | Path | None = None):
    # Load vessel facts first so the tariff rules are evaluated for the actual vessel.
    """
    print("1. Loading vessel profile...")
    vessel = vessel_profile()

    vessel_context = {
        "vessel_name": vessel.get("vessel_name"),
        "vessel_type": vessel.get("vessel_type"), # or extracted_entities.get("vessel_type"),
        "gross_tonnage": vessel.get("gross_tonnage"), # or extracted_entities.get("gross_tonnage"),
        "length_overall": vessel.get("length_overall"),
        "cargo_quantity": vessel.get("cargo_quantity"),
        "days_alongside": vessel.get("days_alongside"),
        "activity": vessel.get("activity"),
        }
    """
    print("2. Initializing Vector Database...")
    vector_store = (
        initialize_vector_store()
    )  # embeddings are initialized within this function

    print("3. Extracting parameters from prompt...")
    extractor = PromptExtractor()
    extracted_entities = extractor.extract(user_query)
    print(f"Extracted Entities: {extracted_entities}")

    print("4. Retrieving relevant tariff rules...")
    retriever = TariffRetriever(vector_store)
    context = retriever.get_relevant_context(user_query)

    print("5. Generating calculations and response via Local LLM...")

    # llm = Ollama(model=OLLAMA_MODEL)

    # connect to LM Studio server for LLM
    llm = ChatOpenAI(
        base_url="http://127.0.0.1:1234/v1",  # LM Studio server endpoint
        api_key="lm-studio",
        model="meta-llama-3.1-8b-instruct",  # "google/gemma-4-12b",  # Match the exact model name shown in LM Studio
        temperature=0.1,
    )

    rag_prompt = PromptTemplate.from_template(
        """" Calculate the different tariffs payable by the following vessel berthing at the port of Durban:


        Context Clauses:
        {context}

        User Query: {user_query}
        Extracted Variables: {entities}

        Provide a structured, step-by-step breakdown:"""
    )

    final_prompt = rag_prompt.format(
        context=context, user_query=user_query, entities=extracted_entities
    )

    response = llm.invoke(final_prompt)

    if output_path is not None:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(
            render_markdown_output(
                user_query=user_query,
                extracted_entities=extracted_entities,
                context=context,
                response=response,
            ),
            encoding="utf-8",
        )
        print(f"Markdown output saved to: {output_file}")

    return response


if __name__ == "__main__":
    print("Starting tariff calculation pipeline...")
    sample_query = "Calculate the different tariffs payable by the following vessel berthing at the port of Durban"
    output_file = Path("output/tariff_calculation.md")

    result = run_pipeline(sample_query, output_file)
    print("\n=== Tariff Calculation Output ===\n")
    print(result)
