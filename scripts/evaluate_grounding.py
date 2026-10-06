from __future__ import annotations
import argparse, csv, hashlib, json, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
from digital_twin.evaluation.research_adapter import ResearchModelAdapter, ResearchModelError, EXPECTED_DIGEST
from digital_twin.evaluation.grounding_v2 import deterministic_output_validation, reference_scoring
from digital_twin.evaluation.grounding_schema_v2 import schema as e2_schema

PROTOCOL_SHA = "13A6FA0B05455EB81BB1B2A4979A1396AAC9EF9D4621239CD8D2E71989CD25F1"
LEGACY_WINDOWS_CRLF_SHA = "220FC8D053D8D31F536FF2F0F65DE1358A54AB2A0BB29CE293BF96792AB3814E"
V2_PROTOCOL_SHA = "6E423F63884145AD00273CF26C65B155C1EC11E3E62A1080C94F74DC807CDD0D"
SCHEMA=e2_schema()
OUTPUT_CONTRACT = "Return JSON with fields assessment (string), claims (array of evidence claims with evidence_ids), abstain (boolean), and optional uncertainty_note. Do not infer causes or psychological states."
FIELDS = ["case_id","scenario_family","checkpoint","variant","model_name","model_digest","runtime","generation_parameters","schema_valid","json_parse_valid","citation_evaluable","citation_valid","unknown_evidence_ids","missing_evidence_reference_count","malformed_claim_count","temporal_evaluable","future_observation_reference_count","no_future_observation_valid","causal_claim_count","no_causal_claim_valid","missingness_violation_count","not_due_violation_count","awaiting_marking_violation_count","missing_feed_violation_count","extension_violation_count","optional_resource_violation_count","policy_threshold_violation_count","missing_feed_detected","conflict_detected","insufficient_evidence_detected","semantic_evaluable","semantic_evidence_valid","model_call_succeeded","evidence_diagnostic_evaluable","evidence_valid","citation_valid","semantic_evidence_valid","validator_codes","unsupported_claim_count","contradiction_count","accepted","abstained","correction_required","correction_attempted","correction_success","initial_latency_ms","correction_latency_ms","total_latency_ms","latency_ms","failure_reason","protocol_version","protocol_sha256","legacy_windows_crlf_sha256","case_count","evaluation_git_commit","run_id","timestamp","raw_response","expected_behavior_class","predicted_behavior_class","behavior_correct","expected_evidence_constraint_valid","constraint_results"]
MODEL_VISIBLE_FIELDS = ["checkpoint", "course_policy", "evidence"]
EVALUATION_ONLY_FIELDS = ["case_id", "scenario_family", "expected_behavior_class", "expected_evidence_constraints"]

def model_visible_case(case):
    if "model_input" in case:
        return case["model_input"]
    return {key: case[key] for key in ("checkpoint", "course_policy", "permitted_evidence") if key in case}

def git_commit():
    return subprocess.run(["git","rev-parse","HEAD"],capture_output=True,text=True).stdout.strip() or "unknown"
def protocol(path):
    raw=Path(path).read_bytes(); canonical=raw.decode("utf-8").replace("\r\n","\n").replace("\r","\n").encode("utf-8"); digest=hashlib.sha256(canonical).hexdigest().upper()
    doc=json.loads(raw)
    expected_hash = V2_PROTOCOL_SHA if doc.get("protocol_version")=="v2" else PROTOCOL_SHA
    if digest != expected_hash: raise SystemExit(f"PROTOCOL_HASH_MISMATCH:{digest}")
    if len(doc.get("cases",[])) != 48: raise SystemExit("PROTOCOL_CASE_COUNT_MISMATCH")
    return doc,digest
def validate(parsed, case):
    if not isinstance(parsed,dict) or not all(k in parsed for k in ("assessment","claims","abstain")):
        return False,False,1,0
    claims=parsed.get("claims"); unsupported=0; contradiction=0; refs=[]
    if isinstance(claims,list):
        for claim in claims:
            if not isinstance(claim,dict): unsupported += 1; continue
            refs.extend(claim.get("evidence_ids",[]) if isinstance(claim.get("evidence_ids",[]),list) else [])
    else: unsupported += 1
    permitted=set(model_visible_case(case).get("permitted_evidence",[]))
    unsupported += sum(1 for ref in refs if ref not in permitted)
    if parsed.get("assessment") and "cause" in str(parsed.get("assessment")).lower(): contradiction += 1
    evidence_valid=unsupported==0 and contradiction==0
    return True,evidence_valid,unsupported,contradiction
def reference_scores(parsed, case):
    predicted = ("abstention_expected" if isinstance(parsed, dict) and parsed.get("abstain") is True else "assessment_allowed" if isinstance(parsed, dict) and parsed.get("abstain") is False else None) if "model_input" in case else (parsed.get("behavior_class") if isinstance(parsed, dict) else None)
    reference=case.get("evaluation_reference",case)
    expected = reference.get("expected_behavior_class")
    constraints = parsed.get("evidence_constraints") if isinstance(parsed, dict) else None
    expected_constraints = reference.get("expected_evidence_constraints") or []
    constraint_ok = isinstance(constraints, list) and set(expected_constraints).issubset(set(constraints))
    return expected, predicted, (predicted == expected if predicted is not None else None), constraint_ok if constraints is not None else None
def run_case(adapter, case, variant, model_digest, run_id, commit, protocol_sha, protocol_version="v1"):
    visible=model_visible_case(case); base={"case":visible,"task":"Assess only the supplied case. Do not infer causes. Cite only permitted evidence categories.","output_contract":OUTPUT_CONTRACT}
    schema=e2_schema() if variant != "plain_llm" else None
    reference=case.get("evaluation_reference",case); checkpoint=case.get("checkpoint"); checkpoint=checkpoint if checkpoint is not None else model_visible_case(case).get("checkpoint",{}).get("week") if isinstance(model_visible_case(case).get("checkpoint",{}),dict) else model_visible_case(case).get("checkpoint"); row={"case_id":case["case_id"],"scenario_family":case["scenario_family"],"checkpoint":checkpoint,"variant":variant,"model_name":adapter.runtime.model_name,"model_digest":model_digest,"runtime":"ollama","generation_parameters":json.dumps(adapter.runtime.generation,sort_keys=True),"schema_valid":False,"json_parse_valid":False,"model_call_succeeded":False,"evidence_diagnostic_evaluable":False,"evidence_valid":False,"unsupported_claim_count":"","contradiction_count":"","accepted":False,"abstained":False,"correction_required":False,"correction_attempted":False,"correction_success":False,"initial_latency_ms":"","correction_latency_ms":"","total_latency_ms":"","latency_ms":"","failure_reason":"","protocol_version":protocol_version,"protocol_sha256":protocol_sha,"legacy_windows_crlf_sha256":LEGACY_WINDOWS_CRLF_SHA,"case_count":48,"evaluation_git_commit":commit,"run_id":run_id,"timestamp":datetime.now(timezone.utc).isoformat(),"raw_response":"","expected_behavior_class":reference.get("expected_behavior_class"),"predicted_behavior_class":"","behavior_correct":"","expected_evidence_constraint_valid":""}
    try:
        result=adapter.generate(base,prompt=json.dumps(base,sort_keys=True),system=OUTPUT_CONTRACT,schema=schema,allow_non_json=(variant=="plain_llm"))
        parsed=result["parsed"]; row.update(model_call_succeeded=True,json_parse_valid=result.get("json_parse_valid",parsed is not None),raw_response=result.get("raw","")[:65536],initial_latency_ms=result["metadata"].get("latency_ms",""),total_latency_ms=result["metadata"].get("latency_ms",""),latency_ms=result["metadata"].get("latency_ms",""))
        if parsed is None:
            return row
        if "model_input" in case:
            vr=deterministic_output_validation(parsed, visible); scored=reference_scoring(vr, parsed, case["evaluation_reference"]); sv=vr.schema_valid; ev=vr.semantic_evidence_valid; uc=vr.unsupported_claim_count; cc=vr.contradiction_count; row.update(schema_valid=sv,evidence_diagnostic_evaluable=vr.semantic_evaluable,evidence_valid=ev,unsupported_claim_count=uc,contradiction_count=cc,validator_codes=json.dumps(vr.validator_codes),citation_valid=vr.citation_valid,semantic_evidence_valid=vr.semantic_evidence_valid,**scored)
        else:
            sv,ev,uc,cc=validate(parsed,case); row.update(schema_valid=sv,evidence_diagnostic_evaluable=True,evidence_valid=ev,unsupported_claim_count=uc,contradiction_count=cc)
        if variant=="evidence_first_full" and not ev:
            row["correction_required"]=True; row["correction_attempted"]=True
            feedback={"case":visible,"prior_output":parsed,"validator_feedback":{"unsupported_claim_count":uc,"contradiction_count":cc},"instruction":"Correct only evidence references and unsupported claims using the same permitted evidence. Return the same JSON schema. Do not invent evidence."}
            corrected=adapter.generate(feedback,prompt=json.dumps(feedback,sort_keys=True),system=OUTPUT_CONTRACT,schema=e2_schema())
            csvv=corrected["parsed"]; clat=corrected["metadata"].get("latency_ms","");
            if "model_input" in case:
                vr2=deterministic_output_validation(csvv,visible); row.update(vr2.to_dict()); row.update(reference_scoring(vr2,csvv,case["evaluation_reference"])); row["validator_codes"]=json.dumps(vr2.validator_codes); sv2,ev2=vr2.schema_valid,vr2.semantic_evidence_valid
            else:
                sv2,ev2,uc2,cc2=validate(csvv,case); row.update(schema_valid=sv2,evidence_valid=ev2,unsupported_claim_count=uc2,contradiction_count=cc2)
            row.update(evidence_diagnostic_evaluable=True,correction_success=bool(sv2 and ev2),correction_latency_ms=clat,total_latency_ms=(row["initial_latency_ms"] or 0)+(clat or 0),latency_ms=(row["initial_latency_ms"] or 0)+(clat or 0),raw_response=corrected.get("raw","")[:65536])
        final_parsed = csvv if variant=="evidence_first_full" and row["correction_attempted"] else parsed
        expected,predicted,behavior_correct,constraint_correct=reference_scores(final_parsed,case); row.update(predicted_behavior_class=predicted or "",behavior_correct="" if behavior_correct is None else behavior_correct,expected_evidence_constraint_valid="" if constraint_correct is None else constraint_correct)
        row["abstained"]=bool(isinstance(final_parsed,dict) and final_parsed.get("abstain") is True)
        row["accepted"]=bool(row["schema_valid"] and (variant!="evidence_first_full" or row["evidence_valid"]) and not row["abstained"])
    except ResearchModelError as exc:
        row["failure_reason"]=exc.code
    except Exception as exc:
        row["failure_reason"]=type(exc).__name__
    return row
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--scenarios",default="evaluation/protocols/e2_grounding_heldout_v1.json"); p.add_argument("--variant",choices=["plain_llm","schema_only","evidence_first_full"]); p.add_argument("--model",required=True); p.add_argument("--output-dir",default="evaluation/results"); p.add_argument("--run-id"); p.add_argument("--all-variants",action="store_true"); a=p.parse_args(argv)
    variants=["plain_llm","schema_only","evidence_first_full"] if a.all_variants else [a.variant]
    if not a.all_variants and not a.variant: p.error("--variant or --all-variants is required")
    doc,psha=protocol(a.scenarios); adapter=ResearchModelAdapter(); readiness=adapter.readiness(verify_generation=True)
    if readiness.get("inference_verified") is not True: raise SystemExit("MODEL_NOT_READY")
    if adapter.runtime.model_name != a.model: raise SystemExit("MODEL_IDENTITY_MISMATCH")
    meta=adapter.metadata(); run_id=a.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"); outdir=Path(a.output_dir); outdir.mkdir(parents=True,exist_ok=True); commit=git_commit()
    for variant in variants:
        path=outdir/f"e2_grounding_{variant}_{run_id}.csv"
        if path.exists(): raise SystemExit(f"REFUSING_TO_OVERWRITE:{path}")
        with path.open("w",newline="",encoding="utf-8") as h:
            w=csv.DictWriter(h,fieldnames=FIELDS); w.writeheader()
            for index, case in enumerate(doc["cases"], 1):
                w.writerow(run_case(adapter,case,variant,meta["digest"],run_id,commit,psha,doc.get("protocol_version","v1"))); h.flush()
                print(f"[E2][{variant}] {index}/48 {case['case_id']} completed", flush=True)
        rows=list(csv.DictReader(path.open(encoding="utf-8"))); total=len(rows)
        evaluable=[r for r in rows if r["evidence_diagnostic_evaluable"]=="True"]; summary={"run_id":run_id,"variant":variant,"protocol_version":doc.get("protocol_version","v1"),"total_cases":len(doc["cases"]),"completed_cases":sum(r["model_call_succeeded"]=="True" for r in rows),"failed_cases":sum(bool(r["failure_reason"]) for r in rows),"model_call_success_count":sum(r["model_call_succeeded"]=="True" for r in rows),"json_parseable_count":sum(r["json_parse_valid"]=="True" for r in rows),"evidence_evaluable_count":len(evaluable),"failed_inference_count":sum(bool(r["failure_reason"]) for r in rows),"schema_valid_rate":sum(r["schema_valid"]=="True" for r in rows)/total,"evidence_valid_rate":sum(r["evidence_valid"]=="True" for r in evaluable)/len(evaluable) if evaluable else None,"accepted_rate":sum(r["accepted"]=="True" for r in rows)/total,"abstention_rate":sum(r["abstained"]=="True" for r in rows)/total,"unsupported_claim_rate":sum(int(r["unsupported_claim_count"])>0 for r in evaluable)/len(evaluable) if evaluable else None,"contradiction_rate":sum(int(r["contradiction_count"])>0 for r in evaluable)/len(evaluable) if evaluable else None,"model":meta,"protocol_version":doc.get("protocol_version","v1"),"protocol_sha256":psha,"legacy_windows_crlf_sha256":LEGACY_WINDOWS_CRLF_SHA,"case_count":48,"scenario_family":{}}
        behavior=[r for r in rows if r["behavior_correct"] in {"True","False"}]; constraints=[r for r in rows if r["expected_evidence_constraint_valid"] in {"True","False"}]
        summary.update(model_visible_fields=(MODEL_VISIBLE_FIELDS if doc.get("protocol_version")=="v2" else ["checkpoint","course_policy","permitted_evidence"]),evaluation_only_fields=EVALUATION_ONLY_FIELDS,behavior_accuracy=sum(r["behavior_correct"]=="True" for r in behavior)/len(behavior) if behavior else None,behavior_correct_count=sum(r["behavior_correct"]=="True" for r in behavior),evidence_constraint_accuracy=sum(r["expected_evidence_constraint_valid"]=="True" for r in constraints)/len(constraints) if constraints else None)
        for family in sorted({r["scenario_family"] for r in rows}): summary["scenario_family"][family]={"total":sum(r["scenario_family"]==family for r in rows),"accepted":sum(r["accepted"]=="True" and r["scenario_family"]==family for r in rows)}
        if variant=="evidence_first_full":
            attempts=sum(r["correction_attempted"]=="True" for r in rows); success=sum(r["correction_success"]=="True" for r in rows); summary.update(correction_attempt_count=attempts,correction_success_count=success,correction_success_rate=success/attempts if attempts else 0,post_correction_acceptance=sum(r["correction_success"]=="True" for r in rows)/total)
        summary_path=outdir/f"e2_grounding_{variant}_{run_id}_summary.json"; summary_path.write_text(json.dumps(summary,indent=2),encoding="utf-8"); print(f"[E2][{variant}] summary={summary_path}", flush=True)
if __name__=="__main__": main()












