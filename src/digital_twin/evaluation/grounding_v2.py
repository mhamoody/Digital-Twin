from __future__ import annotations
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any

CONSTRAINTS={"cite_only_permitted_ids","no_future_observation","no_causal_claim","do_not_treat_missing_as_zero","do_not_treat_not_due_as_missing","do_not_treat_awaiting_marking_as_failure","missing_feed_requires_abstention","conflict_requires_abstention","insufficient_evidence_requires_abstention","respect_approved_extension","respect_optional_resource"}
CAUSAL=re.compile(r"unmotivated|lazy|does not care|lack of engagement caused|because the (?:student|learner) is|motivation explains",re.I)
@dataclass
class ValidationResult:
 schema_valid: bool=False; citation_evaluable: bool=False; citation_valid: bool=False
 unknown_evidence_ids:int=0; missing_evidence_reference_count:int=0; malformed_claim_count:int=0
 temporal_evaluable: bool=False; future_observation_reference_count:int=0; no_future_observation_valid: bool=False
 causal_claim_count:int=0; no_causal_claim_valid: bool=False
 missingness_violation_count:int=0; not_due_violation_count:int=0; awaiting_marking_violation_count:int=0
 missing_feed_violation_count:int=0; extension_violation_count:int=0; optional_resource_violation_count:int=0
 policy_threshold_violation_count:int=0; missing_feed_detected:bool=False; conflict_detected:bool=False; insufficient_evidence_detected:bool=False
 semantic_evaluable:bool=False; semantic_evidence_valid:bool=False; unsupported_claim_count:int=0; contradiction_count:int=0
 validator_codes:list[str]=None
 def __post_init__(self):
  if self.validator_codes is None:self.validator_codes=[]
 def to_dict(self): return asdict(self)

def _text(claim): return str(claim.get("claim","")) if isinstance(claim,dict) else ""
def deterministic_output_validation(model_output:dict, model_input:dict)->ValidationResult:
 r=ValidationResult(); evidence={e.get("evidence_id"):e for e in model_input.get("evidence",[]) if isinstance(e,dict)}; claims=model_output.get("claims") if isinstance(model_output,dict) else None
 r.schema_valid=isinstance(model_output,dict) and isinstance(model_output.get("assessment"),str) and isinstance(claims,list) and isinstance(model_output.get("abstain"),bool)
 if not r.schema_valid:r.validator_codes.append("SCHEMA_INVALID"); return r
 r.citation_evaluable=True; refs=[]
 for c in claims:
  if not isinstance(c,dict) or not isinstance(c.get("claim"),str) or "evidence_ids" not in c or not isinstance(c["evidence_ids"],list):
   r.malformed_claim_count+=1; r.validator_codes.append("MALFORMED_CLAIM"); continue
  if not c["evidence_ids"]:r.missing_evidence_reference_count+=1
  refs.extend(c["evidence_ids"])
 unknown=[x for x in refs if not isinstance(x,str) or x not in evidence]; r.unknown_evidence_ids=len(unknown)
 r.citation_valid=not (r.malformed_claim_count or r.missing_evidence_reference_count or r.unknown_evidence_ids)
 if not r.citation_valid:r.validator_codes.append("CITATION_INVALID")
 cp=model_input.get("checkpoint",{}).get("timestamp",""); r.temporal_evaluable=True
 for ref in refs:
  e=evidence.get(ref)
  if e and e.get("observed") and e.get("source_time") and e["source_time"]>cp:r.future_observation_reference_count+=1
 r.no_future_observation_valid=r.future_observation_reference_count==0
 if not r.no_future_observation_valid:r.validator_codes.append("FUTURE_OBSERVATION")
 alltext=" ".join(_text(c) for c in claims)
 r.causal_claim_count=len(CAUSAL.findall(alltext)); r.no_causal_claim_valid=r.causal_claim_count==0
 if not r.no_causal_claim_valid:r.validator_codes.append("CAUSAL_CLAIM")
 policy=model_input.get("course_policy",{}); due=policy.get("assessment_due_time")
 missing_grade=any(e.get("evidence_type")=="grade" and e.get("observed") is False for e in evidence.values())
 zero_claim=bool(re.search(r"zero|failing|failed grade|grade.*missing",alltext,re.I))
 if missing_grade and zero_claim:r.missingness_violation_count+=1
 if due and cp<due and re.search(r"overdue|late|missed deadline|failed to submit",alltext,re.I):r.not_due_violation_count+=1
 awaiting=any(e.get("value",{}).get("status")=="awaiting_marking" for e in evidence.values() if isinstance(e.get("value"),dict))
 if awaiting and re.search(r"zero|failed|non-submission|missed assessment",alltext,re.I):r.awaiting_marking_violation_count+=1
 feed=any(e.get("evidence_type")=="activity" and e.get("observed") is False for e in evidence.values()); r.missing_feed_detected=feed
 if feed and re.search(r"inactiv|no activity|inactive",alltext,re.I):r.missing_feed_violation_count+=1
 extension=next((e for e in evidence.values() if e.get("evidence_type")=="extension" and isinstance(e.get("value"),dict) and e["value"].get("approved")),None)
 if extension and extension.get("value",{}).get("new_due_time") and cp<extension["value"]["new_due_time"] and re.search(r"overdue|late|missed deadline",alltext,re.I):r.extension_violation_count+=1
 if not policy.get("resource_required",True) and re.search(r"mandatory|required.*miss|non-compliance",alltext,re.I):r.optional_resource_violation_count+=1
 threshold=policy.get("inactivity_concern_after_days"); days=next((e.get("value",{}).get("days_since_last_activity") for e in evidence.values() if isinstance(e.get("value"),dict) and "days_since_last_activity" in e.get("value",{})),None)
 if threshold is not None and days is not None and days<threshold and re.search(r"exceed.*threshold|inactivity concern",alltext,re.I):r.policy_threshold_violation_count+=1
 r.conflict_detected=any(e.get("evidence_type")=="activity" and isinstance(e.get("value"),dict) and e["value"].get("events_last_7_days",0)>10 for e in evidence.values()) and any(e.get("evidence_type")=="activity" and isinstance(e.get("value"),dict) and e["value"].get("days_since_last_activity",0)<=1 for e in evidence.values())
 r.insufficient_evidence_detected=not any(e.get("observed") for e in evidence.values())
 violations=r.causal_claim_count+r.missingness_violation_count+r.not_due_violation_count+r.awaiting_marking_violation_count+r.missing_feed_violation_count+r.extension_violation_count+r.optional_resource_violation_count+r.policy_threshold_violation_count
 r.unsupported_claim_count=violations; r.contradiction_count=violations; r.semantic_evaluable=True; r.semantic_evidence_valid=violations==0 and r.citation_valid and r.no_future_observation_valid and r.no_causal_claim_valid
 return r

def reference_scoring(validation_result:ValidationResult, model_output:dict, evaluation_reference:dict)->dict:
 abstain=model_output.get("abstain") if isinstance(model_output,dict) else None
 predicted="abstention_expected" if abstain is True else "assessment_allowed" if abstain is False else None
 expected=evaluation_reference.get("expected_behavior_class")
 checks={"cite_only_permitted_ids":validation_result.citation_valid,"no_future_observation":validation_result.no_future_observation_valid,"no_causal_claim":validation_result.no_causal_claim_valid,"do_not_treat_missing_as_zero":validation_result.missingness_violation_count==0,"do_not_treat_not_due_as_missing":validation_result.not_due_violation_count==0,"do_not_treat_awaiting_marking_as_failure":validation_result.awaiting_marking_violation_count==0,"missing_feed_requires_abstention":not validation_result.missing_feed_detected or abstain is True,"conflict_requires_abstention":not validation_result.conflict_detected or abstain is True,"insufficient_evidence_requires_abstention":not validation_result.insufficient_evidence_detected or abstain is True,"respect_approved_extension":validation_result.extension_violation_count==0,"respect_optional_resource":validation_result.optional_resource_violation_count==0}
 unknown=set(evaluation_reference.get("expected_evidence_constraints",[]))-CONSTRAINTS
 if unknown: raise ValueError(f"UNKNOWN_CONSTRAINT:{sorted(unknown)}")
 return {"predicted_behavior_class":predicted,"behavior_correct":predicted==expected if predicted is not None else None,"expected_evidence_constraint_valid":all(checks[c] for c in evaluation_reference.get("expected_evidence_constraints",[])),"constraint_results":checks}


