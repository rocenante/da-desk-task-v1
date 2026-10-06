"""Tests for tariff-rate extraction and calculation helpers."""

from src.main import (
    calculate_tariffs,
    calculate_tiered_charge,
    extract_rate_inputs_from_context,
    render_markdown_output,
)


def test_render_markdown_output_is_human_readable():
    markdown = render_markdown_output(
        user_query="Calculate light dues for a 35,000 GT vessel",
        extracted_entities={"gross_tonnage": 35000, "services": ["light dues"]},
        context="Light dues are R24.64 per metre.",
        response="The light dues are R1,000.",
    )

    assert markdown.startswith("# Tariff Calculation Output\n")
    assert "## User Query" in markdown
    assert "Calculate light dues for a 35,000 GT vessel" in markdown
    assert "## Extracted Entities" in markdown
    assert "gross_tonnage: 35000" in markdown
    assert "## Relevant Tariff Context" in markdown
    assert "Light dues are R24.64 per metre." in markdown
    assert "## Model Response" in markdown
    assert "The light dues are R1,000." in markdown


def test_calculate_tiered_charge_uses_python_for_incremental_gt():
    tiers = [
        {"up_to": 50000, "base_fee": 10000, "rate": 0},
        {"up_to": None, "base_fee": 0, "rate": 2},
    ]

    assert calculate_tiered_charge(51300, tiers) == 12600


def test_calculate_tariffs_applies_extracted_tiers_to_vessel_gt():
    result = calculate_tariffs(
        {"gross_tonnage": 51300, "length_overall": 229.2},
        {},
        {
            "port_dues_tiers": [
                {"up_to": 50000, "base_fee": 10000, "rate": 0},
                {"up_to": None, "base_fee": 0, "rate": 2},
            ]
        },
    )

    assert result["port_dues"] == 12600


def test_extract_rate_inputs_from_context_parses_tariff_rates():
    context = """
    1.1.1 LIGHT DUES
    Per metre or part thereof of the length overall per financial year or part thereof................24.64
    """

    rate_inputs = extract_rate_inputs_from_context(context)

    assert rate_inputs["light_dues_rate"] == 24.64
    assert rate_inputs["light_dues_basis"] == "per metre of length overall"


def test_extract_rate_inputs_from_context_does_not_use_defaults():
    rate_inputs = extract_rate_inputs_from_context(
        "The requested tariff section was not found."
    )

    assert rate_inputs["light_dues_rate"] is None
    assert rate_inputs["port_dues_rate"] is None
    assert rate_inputs["tug_rate"] is None
    assert rate_inputs["vts_rate"] is None
