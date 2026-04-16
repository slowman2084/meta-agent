import re

text = "**平均得分**: **92.5 / 100**"

patterns = [
    r"平均得分\s*[：:|]\s*\**(\d+\.?\d*)",
    r"平均分\s*[：:|]\s*\**(\d+\.?\d*)",
    r"平均(?:得)?分\s*[*]*\s*[：:|]\s*[*]*\s*(\d+\.?\d*)",
    r"avg(?:_score)?\s*[*]*\s*[：:=]\s*[*]*\s*(\d+\.?\d*)"
]

for p in patterns:
    match = re.search(p, text, flags=re.IGNORECASE)
    print(f"{p} -> {match.group(1) if match else None}")
