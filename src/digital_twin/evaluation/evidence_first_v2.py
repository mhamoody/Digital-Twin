from __future__ import annotations
from digital_twin.evaluation.grounding_v2 import deterministic_output_validation

def diagnostics(v, model_input):
    checks={"cite_only_permitted_ids":v.citation_valid,"no_future_observation":v.no_future_observation_valid,"no_causal_claim":v.no_causal_claim_valid,"do_not_treat_missing_as_zero":v.missingness_violation_count==0,"do_not_treat_not_due_as_missing":v.not_due_violation_count==0,"do_not_treat_awaiting_marking_as_failure":v.awaiting_marking_violation_count==0,"missing_feed_requires_abstention":not v.missing_feed_detected or False,"conflict_requires_abstention":not v.conflict_detected or False,"insufficient_evidence_requires_abstention":not v.insufficient_evidence_detected or False,"respect_approved_extension":v.extension_violation_count==0,"respect_optional_resource":v.optional_resource_violation_count==0}
    return {k:v for k,v in checks.items() if v is False}

def quality(v, output):
    abstain=bool(isinstance(output,dict) and output.get('abstain') is True)
    required=(not v.missing_feed_detected and not v.conflict_detected and not v.insufficient_evidence_detected) or abstain
    return (bool(v.full_output_contract_valid),bool(v.citation_valid),bool(v.semantic_evidence_valid),required,-v.contradiction_count,-v.unsupported_claim_count)

def select(initial, corrected, model_input):
    vi=deterministic_output_validation(initial,model_input); vc=deterministic_output_validation(corrected,model_input)
    qi,qc=quality(vi,initial),quality(vc,corrected)
    if qc>qi: return corrected,'corrected',True,qi,qc
    return initial,'initial','no_strict_improvement',qi,qc
