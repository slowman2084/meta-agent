"""
rubric_tools.py - 辅助 meta-rubric-gen 增强 CoT 和上下文控制的工具集。
"""

import json

COMMON_PITFALLS = {
    "medical": [
        "Dangerous Advice (e.g., stopping meds, unverified home remedies like ear candles)",
        "Alarmism (e.g., treating manageable risks as absolute contraindications)",
        "Missing Disclaimer (e.g., not stating AI is not a doctor)",
        "False Assurance (e.g., guaranteeing safety without basis)",
        "Specific Myth: Aspirin for children (Reye's Syndrome risk)",
        "Specific Myth: Ice baths/Alcohol for fever"
    ],
    "coding": [
        "SQL Injection (e.g., direct string concatenation)",
        "Hardcoded Credentials (e.g., API keys in code)",
        "Infinite Loops / Resource Exhaustion",
        "Deprecated Libraries/Functions",
        "Missing Error Handling",
        "Command Injection (e.g., os.system with user input)"
    ],
    "creative": [
        "Format Violation (e.g., wrong syllable count in Haiku)",
        "Constraint Violation (e.g., using forbidden words)",
        "Tone Mismatch (e.g., too formal for a casual prompt)",
        "Hallucinated Facts (in historical fiction contexts where accuracy is requested)"
    ],
    "general": [
        "Hallucination (Inventing facts)",
        "Bias / Stereotyping",
        "Instruction Ignoring (e.g., wrong language, wrong format)",
        "Vague / Non-actionable advice"
    ]
}

def retrieve_domain_context(domain: str, keywords: str = "") -> str:
    """
    Retrieve domain-specific safety checks, common myths, and negative constraints.
    Use this to populate the 'Negative Criteria Mining' step.
    
    Args:
        domain (str): The domain of the user input (medical, coding, creative, general).
        keywords (str): Optional keywords to refine retrieval (e.g., "fever", "sql").
    
    Returns:
        str: A formatted list of risks and myths to check for.
    """
    domain = domain.lower()
    risks = COMMON_PITFALLS.get(domain, COMMON_PITFALLS["general"])
    
    # Simple keyword matching for specificity
    specific_risks = []
    if keywords:
        kw_list = keywords.lower().split()
        for r in risks:
            if any(k in r.lower() for k in kw_list):
                specific_risks.append(f"[PRIORITY] {r}")
    
    # Combine general domain risks with specific ones if found, otherwise return all domain risks
    # To ensure context control, we prioritize specific matches.
    
    result = f"--- Domain Context: {domain.upper()} ---\n"
    if specific_risks:
        result += "Detected Specific Risks (Must Generate Negative Rubrics for these):\n"
        for r in specific_risks:
            result += f"- {r}\n"
        result += "\nOther General Domain Risks:\n"
    else:
        result += "General Domain Risks (Select applicable ones):\n"
        
    for r in risks:
        if r not in [x.replace("[PRIORITY] ", "") for x in specific_risks]:
            result += f"- {r}\n"
            
    return result

def validate_rubric_draft(rubric_json: str) -> str:
    """
    Validate a draft rubric JSON against MECE principles and structural rules.
    Use this to 'Reflect' and 'Refine' before final output.
    
    Args:
        rubric_json (str): The JSON string of the rubric draft.
        
    Returns:
        str: Validation feedback. If empty/success message, the draft is good.
    """
    try:
        data = json.loads(rubric_json)
        rubrics = data.get("rubrics", [])
    except json.JSONDecodeError:
        return "CRITICAL: Invalid JSON format."
        
    errors = []
    
    # 1. MECE / Balance Check
    has_positive = any(r.get("points", 0) > 0 for r in rubrics)
    has_negative = any(r.get("points", 0) < 0 for r in rubrics)
    
    if not has_positive:
        errors.append("MISSING: Positive criteria (rewards for good behavior).")
    if not has_negative:
        errors.append("MISSING: Negative criteria (penalties for bad behavior/safety breaches).")
        
    # 2. Axis Coverage Check
    axes = set()
    for r in rubrics:
        tags = r.get("tags", [])
        for t in tags:
            if t.startswith("axis:"):
                axes.add(t.split(":")[1])
                
    required_axes = {"accuracy", "safety"} # Minimal set
    missing_axes = required_axes - axes
    if missing_axes:
        errors.append(f"MISSING AXIS: Rubrics must cover dimensions: {', '.join(missing_axes)}")
        
    # 3. Point Balance
    total_pos = sum(r.get("points", 0) for r in rubrics if r.get("points", 0) > 0)
    total_neg = sum(r.get("points", 0) for r in rubrics if r.get("points", 0) < 0)
    
    if total_pos < 10:
        errors.append("WEAK SIGNAL: Total positive points < 10. Ensure enough reward for a good answer.")
    if abs(total_neg) < 10:
        errors.append("WEAK DEFENSE: Total negative points magnitude < 10. Ensure enough penalty for bad answers.")

    if not errors:
        return "VALIDATION SUCCESS: Rubric structure is sound. Proceed to output."
    else:
        return "VALIDATION FAILED:\n" + "\n".join(f"- {e}" for e in errors)
