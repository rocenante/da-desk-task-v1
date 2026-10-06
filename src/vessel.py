"""Load and normalize vessel details from the project JSON dataset."""

import json
from pathlib import Path

# Resolve the project root once so vessel metadata can be read consistently across
# scripts and notebooks.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_VESSEL_PATH = PROJECT_ROOT / "data" / "vessel.json"


def vessel_profile(json_path: str | Path | None = None):
    """Load vessel details from data/vessel.json and return the requested summary fields."""
    vessel_path = Path(json_path) if json_path is not None else DEFAULT_VESSEL_PATH

    with vessel_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    profile = data.get("Vessel Details", data)
    main_details = profile.get("Main Details", {})
    cargo_details = profile.get("Cargo Details", {})
    activity = profile.get("Activity/Operations", {}).get("Activity")
    general = profile.get("General", {})

    return {
        "vessel_name": general.get("Vessel Name"),
        "vessel_type": main_details.get("Type"),
        "cargo_quantity": cargo_details.get("Cargo Quantity"),
        "days_alongside": cargo_details.get("Days Alongside"),
        "activity": activity,
        "deadweight_tonnage": main_details.get("DWT"),
        "gross_tonnage": main_details.get("GT"),
        "net_tonnage": main_details.get("NT"),
        "length_overall": main_details.get("LOA (m)"),
        "ship_width": main_details.get("Beam (m)"),
        "moulded_depth": main_details.get("Moulded Depth (m)"),
        "ship_length": main_details.get("LBP"),
        "drafts_sw_summer": main_details.get("Drafts SW S (m)"),
        "drafts_sw_winter": main_details.get("Drafts SW W (m)"),
        "drafts_sw_tropical": main_details.get("Drafts SW T (m)"),
        "suez_gross_tonnage": main_details.get("Suez GT"),
        "suez_net_tonnage": main_details.get("Suez NT"),
    }

if __name__ == "__main__":
    profile = vessel_profile()
    print(json.dumps(profile, indent=2, ensure_ascii=False))

#vessel = vessel_profile()
#print(vessel["vessel_name"])
#print(vessel["cargo_quantity"])