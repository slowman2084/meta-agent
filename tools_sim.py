def retrieve_domain_context(domain, keywords):
    # Simulated tool for Agent logic
    contexts = {
        "medical_产后肺炎": {
            "risks": ["误诊为普通感冒", "延误治疗导致败血症", "与肺栓塞（PE）混淆"],
            "key_symptoms": ["高热", "咳嗽（伴痰）", "胸痛", "呼吸急促/困难", "寒战"],
            "advice": ["必须强调即刻就医", "不可自行诊断"]
        }
    }
    return contexts.get(f"{domain}_{keywords}", "General knowledge applies.")

def validate_rubric_draft(rubric_json):
    # Simulated validation logic
    return {"status": "success", "message": "Rubric meets MECE and safety standards."}
