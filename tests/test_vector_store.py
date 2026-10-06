"""Inspect the persisted Chroma tariff collection for debugging and validation."""

import chromadb
import pandas as pd

client = chromadb.PersistentClient(path="chroma_tariff_db")


def collection_to_dataframe(collection_name):
    collection = client.get_collection(collection_name)
    data = collection.get(include=["documents", "metadatas"])
    rows = []

    for document, metadata in zip(data["documents"], data["metadatas"]):
        rows.append({
            "section": metadata.get("tariff_section") or metadata.get("tariff_section_name"),
            "section_id": metadata.get("tariff_section_id"),
            "page": metadata.get("page") or metadata.get("tariff_section_start_page"),
            "text": document,
        })

    return pd.DataFrame(rows)


df = collection_to_dataframe("tariff_sections_v2")
print("tariff_sections_v2 rows:", len(df))
print(df.head())
print(df["section"].value_counts())


## Filter sections with Pandas:
light_dues = df[
    df["section"].str.contains("LIGHT DUES", case=False, na=False)
]

print(light_dues[["section", "page", "text"]].to_string(index=False))

## Search for tariff terms:
#towage = df[
#    df["text"].str.contains(
#        "tug|towage|vessel assistance",
#        case=False,
#        na=False,
#        regex=True,
#    )
#]

# print(towage[["section", "page", "text"]].to_string(index=False))
#
#print(towage[["section", "page"]].to_string(index=False))

#v3 = collection_to_dataframe("tariff_sections_v3")
#print("tariff_sections_v3 rows:", len(v3))
#if v3.empty:
#    print("tariff_sections_v3 is empty; rebuild the section-aware index before querying it.")