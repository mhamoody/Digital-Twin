from __future__ import annotations

def parse_bool(value):
    if value is True or value is False: return value
    if value is None or value == "": return None
    if isinstance(value,str) and value.lower() in ("true","false"): return value.lower()=="true"
    return None

def rate_with_denominator(rows, field, expected=True):
    vals=[parse_bool(r.get(field)) for r in rows]; vals=[v for v in vals if v is not None]
    return sum(v is expected for v in vals)/len(vals) if vals else None

def build_e2_summary(rows, meta=None, protocol_version="v2", protocol_sha256="", run_id="", variant="plain_llm"):
    meta=meta or {}; total=len(rows); b=lambda r,k:parse_bool(r.get(k)); count=lambda k:sum(b(r,k) is True for r in rows)
    ce=[r for r in rows if b(r,"citation_evaluable") is not None]; se=[r for r in rows if b(r,"semantic_evaluable") is not None]; be=[r for r in rows if b(r,"behavior_correct") is not None]; xe=[r for r in rows if b(r,"expected_evidence_constraint_valid") is not None]
    unsupported=[int(r.get("unsupported_claim_count") or 0) for r in se]; contradictions=[int(r.get("contradiction_count") or 0) for r in se]
    s={"run_id":run_id,"variant":variant,"protocol_version":protocol_version,"protocol_sha256":protocol_sha256,"total_cases":total,"completed_cases":sum(b(r,"model_call_succeeded") is True for r in rows),"failed_cases":sum(bool(r.get("failure_reason")) for r in rows),"failed_inference_count":sum(bool(r.get("failure_reason")) for r in rows),"model_call_success_count":sum(b(r,"model_call_succeeded") is True for r in rows),"json_parseable_count":sum(b(r,"json_parse_valid") is True for r in rows),"schema_valid_count":count("schema_valid"),"schema_valid_rate":rate_with_denominator(rows,"schema_valid"),"citation_evaluable_count":len(ce),"citation_valid_count":sum(b(r,"citation_valid") is True for r in ce),"citation_valid_rate":rate_with_denominator(ce,"citation_valid"),"semantic_evaluable_count":len(se),"semantic_evidence_valid_count":sum(b(r,"semantic_evidence_valid") is True for r in se),"semantic_evidence_valid_rate":rate_with_denominator(se,"semantic_evidence_valid"),"unsupported_claim_case_count":sum(x>0 for x in unsupported),"unsupported_claim_total":sum(unsupported),"unsupported_claim_rate":sum(x>0 for x in unsupported)/len(unsupported) if unsupported else None,"contradiction_case_count":sum(x>0 for x in contradictions),"contradiction_total":sum(contradictions),"contradiction_rate":sum(x>0 for x in contradictions)/len(contradictions) if contradictions else None,"accepted_count":count("accepted"),"accepted_rate":rate_with_denominator(rows,"accepted"),"abstention_count":count("abstained"),"abstention_rate":rate_with_denominator(rows,"abstained"),"behavior_evaluable_count":len(be),"behavior_correct_count":sum(b(r,"behavior_correct") is True for r in be),"behavior_accuracy":rate_with_denominator(be,"behavior_correct"),"evidence_constraint_evaluable_count":len(xe),"evidence_constraint_correct_count":sum(b(r,"expected_evidence_constraint_valid") is True for r in xe),"evidence_constraint_accuracy":rate_with_denominator(xe,"expected_evidence_constraint_valid"),"model":meta,"model_visible_fields":["checkpoint","course_policy","evidence"],"evaluation_only_fields":["case_id","scenario_family","expected_behavior_class","expected_evidence_constraints"],"scenario_family":{}}
    for fam in sorted({r.get("scenario_family","") for r in rows}):
        fr=[r for r in rows if r.get("scenario_family")==fam]; s["scenario_family"][fam]={"total":len(fr),"behavior_accuracy":rate_with_denominator(fr,"behavior_correct"),"citation_valid_rate":rate_with_denominator([r for r in fr if b(r,"citation_evaluable") is not None],"citation_valid"),"semantic_evidence_valid_rate":rate_with_denominator([r for r in fr if b(r,"semantic_evaluable") is not None],"semantic_evidence_valid"),"constraint_accuracy":rate_with_denominator([r for r in fr if b(r,"expected_evidence_constraint_valid") is not None],"expected_evidence_constraint_valid")}
    attempts=count("correction_attempted")
    if variant=="evidence_first_full": s.update(correction_attempt_count=attempts,correction_success_count=count("correction_success"),correction_success_rate=rate_with_denominator([r for r in rows if b(r,"correction_attempted") is True],"correction_success"))
    return s
