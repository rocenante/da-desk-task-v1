"""Retrieve the most relevant tariff clauses for a user request from the Chroma store."""

import re

from langchain_core.documents import Document


class TariffRetriever:
    # Most of the retrieval work is driven by semantic search queries built from the
    # user request, then expanded into the full section information for better context.
    def __init__(self, vector_store, documents_per_section: int = 12):
        self.documents_per_section = documents_per_section
        self.retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": documents_per_section},
        )

    def build_search_queries(self, query: str) -> list[str]:
        """Use the request as a semantic query; section names come from the document."""
        clauses = re.split(r",|\band\b", query or "", flags=re.IGNORECASE)
        service_clauses = [
            re.sub(r"^\s*(calculate|provide|show|get|find)\s+", "", clause.strip(), flags=re.IGNORECASE)
            for clause in clauses
            if re.search(r"\b(dues?|charges?|towage|vts|pilotage|lines?)\b", clause, re.IGNORECASE)
        ]
        service_clauses = [
            clause.replace("towage", "towage tugs vessel assistance")
            for clause in service_clauses
        ]
        queries = [f"{clause} tariff rate calculation basis applicable charge" for clause in service_clauses]
        return queries or [f"{query} tariff rates calculation basis applicable charges"]

    def _section_ids(self, documents: list) -> set[str]:
        section_ids = set()
        for document in documents[:self.documents_per_section]:
            section_id = (getattr(document, "metadata", {}) or {}).get("tariff_section_id")
            if section_id:
                section_ids.add(section_id)
        return section_ids

    def _expand_sections(self, documents: list) -> list:
        sections = self._section_ids(documents)
        if not sections or not hasattr(self.retriever, "vectorstore"):
            return []

        expanded = []
        for section in sections:
            result = self.retriever.vectorstore.get(where={"tariff_section_id": section})
            expanded.extend(
                Document(page_content=content, metadata=metadata or {})
                for content, metadata in zip(result.get("documents", []), result.get("metadatas", []))
            )
        return expanded

    def get_relevant_documents(self, query: str) -> list:
        """Retrieve and deduplicate clauses from each requested tariff section."""
        documents = []
        seen = set()

        for search_query in self.build_search_queries(query):
            candidates = self.retriever.invoke(search_query) or []
            section_documents = self._expand_sections(candidates)
            selected_documents = section_documents or candidates
            for document in selected_documents:
                content = document.page_content.strip()
                if content and content not in seen:
                    seen.add(content)
                    documents.append(document)

        return documents

    def get_relevant_context(self, query: str) -> str:
        documents = self.get_relevant_documents(query)
        if not documents:
            return "No relevant tariff clauses were retrieved from the local document store."

        sections = []
        for document in documents:
            metadata = getattr(document, "metadata", {}) or {}
            page = metadata.get("page")
            heading = f"Page {page + 1}" if isinstance(page, int) else "Retrieved tariff clause"
            sections.append(f"[{heading}]\n{document.page_content.strip()}")

        return "\n\n".join(sections)
