import re

IMPORTS = """
from typing import Dict, Tuple, Set, Sequence
from eth2spec.utils.ssz.ssz_typing import Bytes32, uint64
from dataclasses import dataclass
from dascore import get_custody_columns
"""


def extract_code_blocks(text_blob):
    pattern = r"^```(?:\w+)?\s*\n(.*?)(?=^```)```"
    code_blocks = re.findall(pattern, text_blob, re.DOTALL | re.MULTILINE)
    output = ""

    for block in code_blocks:
        output += block
        output += "\n"

    return output


def extract_table_values(text_blob):
    rows = re.findall(r"\|([^|]+)\|([^|]+)\|", text_blob)
    cleaned_rows = [[cell.strip() for cell in row] for row in rows]
    output = ""

    for row in cleaned_rows:
        if "Name" in row or "Value" in row:
            continue
        if "---" in row[0] or "---" in row[1]:
            continue

        output += row[0] + " = " + row[1]
        output += "\n"

    return output


def process_file(filepath):
    output = ""
    output += IMPORTS
    output += "\n\n\n"

    with open(filepath, "r") as f:
        text_blob = f.read()
        output += extract_table_values(text_blob)
        output += "\n\n\n"
        output += extract_code_blocks(text_blob)

    return output


if __name__ == "__main__":
    output = process_file("./rated_list.md")
    with open("./simulator/node.py", "w") as f:
        f.write(output)
