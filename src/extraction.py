## src/extraction.py

"""Extract key vessel and service metadata from a user request."""

import json
import re


class PromptExtractor:
    def extract(self, user_query: str) -> dict:
        # Normalize the input to make matching easier and keep the logic case-insensitive.
        text = (user_query or "").strip()
        lower_text = text.lower()

        port_match = re.search(r"port of\s+([a-zA-Z\s'-]+?)(?:\.|,|$)", lower_text)
        port_name = port_match.group(1).strip().title() if port_match else "Unknown"

        gt_match = re.search(r"(\d[\d,]*)\s*gt", lower_text)
        gross_tonnage = int(gt_match.group(1).replace(",", "")) if gt_match else 0

        vessel_type_match = re.search(r"([a-zA-Z\s-]+?)\s+vessel", lower_text)
        vessel_type = vessel_type_match.group(1).strip() if vessel_type_match else "unknown"

        services = []
        service_map = {
            "light dues": "light dues",
            "port dues": "port dues",
            "towage": "towage dues",
            "towage dues": "towage dues",
            "vts": "VTS dues",
            "vts dues": "VTS dues",
            "pilotage": "pilotage dues",
            "pilotage dues": "pilotage dues",
            "line running": "running of vessel lines dues",
            "running of vessel lines": "running of vessel lines dues",
            "running of vessel lines dues": "running of vessel lines dues",
        }

        for key, label in service_map.items():
            if key in lower_text:
                services.append(label)

        return {
            "port_name": port_name,
            "vessel_type": vessel_type,
            "gross_tonnage": gross_tonnage,
            "services": services,
        }