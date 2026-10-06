# 1. Extract the raw text first (common to all formats)

import re

# Read the file
with open("./output/test result 6 v1.txt", "r", encoding="utf-8") as f:
    raw = f.read()

# Extract everything inside content="..." (handles escaped quotes)
match = re.search(r'content="(.*?)"\s*additional_kwargs=', raw, re.DOTALL)
if not match:
    # Fallback: just take everything after the header line
    match = re.search(r'===\s*Tariff Calculation Output\s*===\s*(.*)', raw, re.DOTALL)

text = match.group(1)

# Decode escape sequences (\n, \t, \", etc.)
text = text.encode("utf-8").decode("unicode_escape")

# Remove the trailing metadata junk if present
text = text.split("additional_kwargs=")[0].strip()

with open("./output/tariff_clean.txt", "w", encoding="utf-8") as f:
    f.write(text)

print(text[:500])  # preview

'''
# 2. Convert to Markdown
 import re

with open("tariff_clean.txt", "r", encoding="utf-8") as f:
    text = f.read()

# Normalize bullets: "*   " -> "- "
text = re.sub(r'^\s*\*\s{2,}', '- ', text, flags=re.MULTILINE)

# Normalize numbered steps: "### Step 1:" already fine, but ensure blank lines
text = re.sub(r'\n{3,}', '\n\n', text)

# Ensure headings have a blank line before/after
text = re.sub(r'(?<!\n)\n(#{1,6} )', r'\n\n\1', text)
text = re.sub(r'(#{1,6} .+)\n(?!\n)', r'\1\n\n', text)

with open("tariff.md", "w", encoding="utf-8") as f:
    f.write(text)

print("Wrote tariff.md")

'''

'''
# 3. Convert to JSON
import json
import re

with open("tariff_clean.txt", "r", encoding="utf-8") as f:
    text = f.read()

data = {"title": "Tariff Calculation for Vessels Berthing at Different Ports", "ports": {}}

current_port = None
current_section = None

for line in text.splitlines():
    line = line.rstrip()
    if not line.strip():
        continue

    # Detect port headings like "#### **Port of Durban**"
    m = re.match(r'#+\s*\*\*Port of (.+?)\*\*', line)
    if m:
        current_port = m.group(1).strip()
        data["ports"].setdefault(current_port, {})
        current_section = None
        continue

    # Detect section headings like "**VTS Charges:**"
    m = re.match(r'\*\*(.+?):\*\*', line)
    if m and current_port:
        current_section = m.group(1).strip()
        data["ports"][current_port].setdefault(current_section, [])
        continue

    # Bullet items
    m = re.match(r'[-*]\s+(.+)', line)
    if m and current_port and current_section:
        data["ports"][current_port][current_section].append(m.group(1).strip())

with open("tariff.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(json.dumps(data, indent=2)[:800])

'''

'''
# 4. Convert to XML
import re
from xml.etree.ElementTree import Element, SubElement, ElementTree, indent

with open("tariff_clean.txt", "r", encoding="utf-8") as f:
    text = f.read()

root = Element("TariffCalculation")
root.set("title", "Tariff Calculation for Vessels Berthing at Different Ports")

ports_el = SubElement(root, "Ports")

current_port_el = None
current_section_el = None

for line in text.splitlines():
    line = line.rstrip()
    if not line.strip():
        continue

    # Port heading
    m = re.match(r'#+\s*\*\*Port of (.+?)\*\*', line)
    if m:
        current_port_el = SubElement(ports_el, "Port", name=m.group(1).strip())
        current_section_el = None
        continue

    # Section heading
    m = re.match(r'\*\*(.+?):\*\*', line)
    if m and current_port_el is not None:
        current_section_el = SubElement(current_port_el, "Section", name=m.group(1).strip())
        continue

    # Bullet line
    m = re.match(r'[-*]\s+(.+)', line)
    if m and current_section_el is not None:
        item = SubElement(current_section_el, "Item")
        item.text = m.group(1).strip()

# Pretty-print (Python 3.9+)
indent(root, space="  ")
ElementTree(root).write("tariff.xml", encoding="utf-8", xml_declaration=True)

print("Wrote tariff.xml")

'''


'''

####  If the file is already inside a JSON-like log line #####
import json
with open("test 6 v1.txt") as f:
    obj = json.load(f)          # if it's valid JSON
text = obj["content"]           # the escaped string
text = text.encode().decode("unicode_escape")
'''