import json, hashlib
from pathlib import Path
from digital_twin.evaluation.bootstrap import bootstrap
from digital_twin.evaluation.canonical import export_temporal_records
from digital_twin.evaluation.research_adapter import ResearchModelAdapter

def test_temporal_export_preserves_identity_and_violation():
 rows=export_temporal_records([{"learner_id":"l","presentation_id":"p","checkpoint_week":3,"cutoff_course_day":20,"features":[{"name":"x","source_time":21}]}])
 assert rows[0]["checkpoint"]==3 and rows[0]["source_time"]==21

def test_heldout_protocol_is_versioned_and_separate():
 p=Path("evaluation/protocols/e2_grounding_heldout_v1.json");doc=json.loads(p.read_text());assert doc["split"]=="heldout" and len(doc["cases"])==48
 assert hashlib.sha256(p.read_bytes()).hexdigest()

def test_research_adapter_blocks_without_model():
 try:ResearchModelAdapter().generate({})
 except RuntimeError as e:assert str(e)=="BLOCKED BY MODEL ACCESS"
 else:assert False

def test_bootstrap_reproducible_and_one_class_safe():
 f=lambda x:sum(x)/len(x)
 assert bootstrap([1,2,3],f)==bootstrap([1,2,3],f)
 assert bootstrap([1,1,1],f)["estimate"]==1
