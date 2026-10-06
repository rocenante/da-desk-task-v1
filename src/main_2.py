"""Alternate tariff-processing implementation kept as a reference/example script."""

import json
import math
import re

from langchain_openai import ChatOpenAI

from src.config import API_KEY, BASE_URL, LM_STUDIO_MODEL
from src.extraction import PromptExtractor
from src.vessel import vessel_profile
from src.ingestion import initialize_vector_store
from src.retriever import TariffRetriever


def _parse_decimal_number(raw_value: str) -> float:
    cleaned = (raw_value or "").replace("R", "").replace("$", "").replace(",", "").replace("%", "").strip()
    if not cleaned:
        return 0.0
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _extract_percent_value(context: str, labels: list[str]) -> float:
    text = _normalize_tariff_numbers(context).lower()
    for label in labels:
        pattern = rf"{re.escape(label)}[:\s\-]*.*?(\d+(?:\.\d+)?)\s*%"
        match = re.search(pattern, text)
        if match:
            return float(match.group(1)) / 100.0

        pattern = rf"{re.escape(label)}[:\s\-]*.*?(\d+(?:\.\d+)?)\s*(?:of gross tonnage|of gt|gross tonnage)"
        match = re.search(pattern, text)
        if match:
            value = float(match.group(1))
            if value > 1:
                value = value / 100.0
            return value

    return 0.0


def _extract_amount_value(context: str, labels: list[str]) -> float:
    text = _normalize_tariff_numbers(context).lower()
    for label in labels:
        pattern = rf"{re.escape(label)}.*?(?:r|rand|rs)?\s*(\d+(?:,\d{{3}})*(?:\.\d+)?)"
        match = re.search(pattern, text)
        if match:
            return _parse_decimal_number(match.group(1))

        pattern = rf"(?:r|rand|rs)?\s*(\d+(?:,\d{{3}})*(?:\.\d+)?)\s*(?:per|/|for)\s*(?:tug|gang|vessel)"
        match = re.search(pattern, text)
        if match:
            return _parse_decimal_number(match.group(1))

    return 0.0


def _extract_per_metre_rate(context: str, label: str) -> float | None:
    context = _normalize_tariff_numbers(context)
    pattern = rf"{re.escape(label)}.*?per metre or part thereof.*?(\d+(?:\.\d+)?)"
    match = re.search(pattern, context or "", flags=re.IGNORECASE | re.DOTALL)
    return float(match.group(1)) if match else None


def _normalize_tariff_numbers(context: str) -> str:
    """Join thousands split by PDF table extraction, such as ``8 140.00``."""
    return re.sub(r"(?<=\d)\s+(?=\d{3}(?:\.\d{2})?\b)", "", context or "")


def _parse_llm_json(response: str) -> dict:
    response_text = getattr(response, "content", response)
    response_text = str(response_text).strip()
    response_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", response_text, flags=re.IGNORECASE)
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        # Some local models add a short explanation or a thinking block around JSON.
        json_start = response_text.find("{")
        json_end = response_text.rfind("}")
        if json_start < 0 or json_end <= json_start:
            raise
        return json.loads(response_text[json_start:json_end + 1])


def extract_tariff_rules_with_llm(context: str, vessel_context: dict, requested_services: list[str]) -> dict:
    """Ask the LLM to select and normalize rules from retrieved tariff clauses.

    The LLM only interprets the document. It must return no rate when the clause
    is absent or the vessel's conditions do not establish applicability.
    """
    prompt = f"""
You are extracting tariff rules from an authoritative port tariff document.
Use only the retrieved clauses below. Do not invent, estimate, or calculate totals.
Select the applicable rule for this vessel and request. Return JSON only.

Vessel and request:
{json.dumps({"vessel": vessel_context, "services": requested_services}, indent=2)}

Retrieved clauses:
{context}

Return this shape. Use null for any unavailable value:
{{
  "light_dues": {{"basis": "per_metre_loa" | "per_100_gt" | null, "rate": number | null, "source": string}},
    "port_dues": {{"basis": string | null, "rate": number | null, "tiers": [{{"up_to": number | null, "base_fee": number, "rate": number}}], "source": string}},
  "vts": {{"basis": "per_gt" | null, "rate": number | null, "minimum_fee": number | null, "source": string}},
  "pilotage": {{"basis": "basic_plus_per_100_gt" | null, "basic_fee": number | null, "rate": number | null, "source": string}},
  "towage": {{"basis": string | null, "rate": number | null, "source": string}},
  "line_running": {{"basis": string | null, "rate": number | null, "source": string}}
}}
"""
    # LM Studio exposes an OpenAI-compatible API; Python performs no tariff arithmetic here.
    response = ChatOpenAI(
        model=LM_STUDIO_MODEL,
        base_url=BASE_URL,
        api_key=API_KEY,
        temperature=0,
        model_kwargs={"response_format": {"type": "json_object"}},
    ).invoke(prompt)
    return _parse_llm_json(response)


def _rules_to_rate_inputs(rules: dict) -> dict:
    light_rule = rules.get("light_dues", {})
    port_rule = rules.get("port_dues", {})
    vts_rule = rules.get("vts", {})
    pilotage_rule = rules.get("pilotage", {})
    towage_rule = rules.get("towage", {})
    line_rule = rules.get("line_running", {})

    return {
        "light_dues_rate": light_rule.get("rate"),
        "light_dues_basis": light_rule.get("basis"),
        "port_dues_rate": port_rule.get("rate"),
        "port_dues_basis": port_rule.get("basis"),
        "port_dues_tiers": port_rule.get("tiers"),
        "vts_rate": vts_rule.get("rate"),
        "vts_minimum_fee": vts_rule.get("minimum_fee"),
        "pilotage_basic_fee": pilotage_rule.get("basic_fee"),
        "pilotage_rate": pilotage_rule.get("rate"),
        "pilotage_basis": pilotage_rule.get("basis"),
        "tug_rate": towage_rule.get("rate"),
        "towage_basis": towage_rule.get("basis"),
        "mooring_gang_rate": line_rule.get("rate"),
        "line_running_basis": line_rule.get("basis"),
        "number_of_tugs": 2,
        "number_of_mooring_gangs": 1,
        "sources": {
            "light_dues": light_rule.get("source"),
            "port_dues": port_rule.get("source"),
            "vts": vts_rule.get("source"),
            "pilotage": pilotage_rule.get("source"),
            "towage": towage_rule.get("source"),
            "line_running": line_rule.get("source"),
        },
    }


def _contains_numeric_rate(rate_inputs: dict) -> bool:
    return any(
        isinstance(rate_inputs.get(rate_name), (int, float)) and rate_inputs[rate_name] > 0
        for rate_name in (
            "light_dues_rate",
            "port_dues_rate",
            "vts_rate",
            "pilotage_rate",
            "tug_rate",
            "mooring_gang_rate",
        )
    ) or bool(rate_inputs.get("port_dues_tiers"))


def extract_rate_inputs_from_context(context: str) -> dict:
    """Extract rate values from retrieved tariff text and normalize them for fee calculations."""
    rate_inputs = {
        "light_dues_rate": _extract_per_metre_rate(context, "light dues"),
        "light_dues_basis": "per metre of length overall",
        "port_dues_rate": _extract_percent_value(context, ["port dues", "port due"]),
        "vts_rate": _extract_percent_value(context, ["vts", "vts charges", "vts dues"]),
        "pilotage_rate": _extract_percent_value(context, ["pilotage"]),
        "tug_rate": _extract_amount_value(
            context,
            ["tug hire", "towage", "tug charges", "tug rate", "tugs/vessel assistance"],
        ),
        "mooring_gang_rate": _extract_amount_value(context, ["mooring gang", "line running", "mooring gang charges"]),
        "number_of_tugs": 2,
        "number_of_mooring_gangs": 1,
    }

    for rate_name in (
        "light_dues_rate",
        "port_dues_rate",
        "vts_rate",
        "pilotage_rate",
        "tug_rate",
        "mooring_gang_rate",
    ):
        if rate_inputs[rate_name] == 0:
            rate_inputs[rate_name] = None

    return rate_inputs


def _calculate_or_flag(base_value: float, rate: float | None, multiplier: int = 1) -> float | str:
    if rate is None or rate <= 0:
        return "NO RATE FOUND"
    return base_value * rate * multiplier


def calculate_tiered_charge(quantity: float, tiers: list[dict] | None) -> float | str:
    """Apply progressive tariff tiers without asking the LLM to do arithmetic."""
    if not tiers:
        return "NO RATE FOUND"

    remaining = max(float(quantity), 0.0)
    previous_limit = 0.0
    total = 0.0
    for tier in tiers:
        upper_limit = tier.get("up_to")
        if upper_limit is None:
            units = remaining
        else:
            upper_limit = float(upper_limit)
            if upper_limit < previous_limit:
                raise ValueError("Tariff tier limits must be in ascending order")
            units = min(remaining, upper_limit - previous_limit)

        if units > 0:
            total += float(tier.get("base_fee") or 0) + units * float(tier.get("rate") or 0)
            remaining -= units
        previous_limit = float(upper_limit) if upper_limit is not None else previous_limit
        if remaining <= 0 or upper_limit is None:
            break

    if remaining > 0:
        return "NO RATE FOUND"
    return total


def calculate_tariffs(vessel_data: dict, extracted_entities: dict, rate_inputs: dict | None = None) -> dict:
    """Calculate dues using the supplied rate inputs and the vessel's GT."""
    if rate_inputs is None:
        rate_inputs = {}

    gross_tonnage = vessel_data.get("gross_tonnage") or extracted_entities.get("gross_tonnage") or 0
    gross_tonnage = int(str(gross_tonnage).replace(",", ""))
    length_overall = vessel_data.get("length_overall")
    length_overall = float(length_overall) if length_overall else 0.0

    return {
        "gross_tonnage": gross_tonnage,
        "length_overall": length_overall,
        "light_dues": (
            _calculate_or_flag(length_overall, rate_inputs.get("light_dues_rate"))
            if rate_inputs.get("light_dues_basis") != "per_100_gt"
            else _calculate_or_flag(math.ceil(gross_tonnage / 100), rate_inputs.get("light_dues_rate"))
        ),
        "port_dues": (
            calculate_tiered_charge(gross_tonnage, rate_inputs.get("port_dues_tiers"))
            if rate_inputs.get("port_dues_tiers")
            else _calculate_or_flag(gross_tonnage, rate_inputs.get("port_dues_rate"))
        ),
        "towage_dues": _calculate_or_flag(1, rate_inputs.get("tug_rate"), int(rate_inputs.get("number_of_tugs", 0))),
        "vts_dues": (
            max(
                _calculate_or_flag(gross_tonnage, rate_inputs.get("vts_rate")),
                rate_inputs.get("vts_minimum_fee") or 0,
            )
            if rate_inputs.get("vts_rate") is not None
            else "NO RATE FOUND"
        ),
        "pilotage_dues": (
            (rate_inputs.get("pilotage_basic_fee") or 0)
            + _calculate_or_flag(math.ceil(gross_tonnage / 100), rate_inputs.get("pilotage_rate"))
            if rate_inputs.get("pilotage_basis") == "basic_plus_per_100_gt"
            and rate_inputs.get("pilotage_basic_fee") is not None
            and rate_inputs.get("pilotage_rate") is not None
            else _calculate_or_flag(gross_tonnage, rate_inputs.get("pilotage_rate"))
        ),
        "running_of_vessel_lines_dues": _calculate_or_flag(1, rate_inputs.get("mooring_gang_rate"), int(rate_inputs.get("number_of_mooring_gangs", 0))),
    }


def run_pipeline(user_query: str, rate_inputs: dict | None = None):
    # Load vessel facts first so the tariff rules are evaluated for the actual vessel.
    print("Loading vessel profile...")
    vessel = vessel_profile()

    # Extract only request parameters here; tariff prices come from the retrieved document.
    print("Extracting parameters from prompt...")
    extractor = PromptExtractor()
    extracted_entities = extractor.extract(user_query)

    vessel_context = {
        "vessel_name": vessel.get("vessel_name"),
        "vessel_type": vessel.get("vessel_type") or extracted_entities.get("vessel_type"),
        "gross_tonnage": vessel.get("gross_tonnage") or extracted_entities.get("gross_tonnage"),
        "length_overall": vessel.get("length_overall"),
        "cargo_quantity": vessel.get("cargo_quantity"),
        "days_alongside": vessel.get("days_alongside"),
        "activity": vessel.get("activity"),
    }

    tariff_rules = {}
    if rate_inputs is None:
        # RAG supplies the tariff clauses that the LLM is allowed to interpret.
        print("Initializing vector database and retrieving relevant tariff clauses...")
        vector_store = initialize_vector_store()
        retriever = TariffRetriever(vector_store)
        context = retriever.get_relevant_context(user_query)
        try:
            # The LLM selects rule structures and rates, but does not calculate money.
            print("Extracting applicable tariff rules with the local LLM...")
            tariff_rules = extract_tariff_rules_with_llm(
                context,
                vessel_context,
                extracted_entities.get("services", []),
            )
            rate_inputs = _rules_to_rate_inputs(tariff_rules)
            if not _contains_numeric_rate(rate_inputs):
                raise ValueError("LLM returned no usable tariff rates")
        except Exception as error:
            # Keep the pipeline usable when JSON normalization fails, without inventing rates.
            print(f"LLM returned invalid tariff rules; rates will be flagged: {error}")
            rate_inputs = extract_rate_inputs_from_context(context)
    else:
        context = "User-supplied rate inputs were used."

    # All arithmetic, including tiered brackets, is executed deterministically in Python.
    tariffs = calculate_tariffs(vessel_context, extracted_entities, rate_inputs)
    # Sum only numeric charges; missing rates remain visible as "NO RATE FOUND".
    total = sum(
        float(value)
        for name, value in tariffs.items()
        if name not in {"gross_tonnage", "length_overall"} and isinstance(value, (int, float))
    )
    tariffs["total_payable"] = total

    return {
        "vessel_context": vessel_context,
        "extracted_entities": extracted_entities,
        "rate_inputs": rate_inputs,
        "tariff_rules": tariff_rules,
        "rag_context": context,
        "tariffs": tariffs,
    }


if __name__ == "__main__":
    sample_query = (
        "Calculate light dues, port dues, towage, VTS, pilotage, and line "
        "running for a 35,000 GT container vessel calling at the Port of Durban."
    )

    result = run_pipeline(sample_query)
    print("\n=== Tariff Calculation Output ===\n")
    print(result["tariffs"])