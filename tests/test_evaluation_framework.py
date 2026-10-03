from digital_twin.evaluation.common import ResultMetadata, append_rows
from digital_twin.evaluation.metrics import binary_metrics
from digital_twin.evaluation.splits import deterministic_split
from digital_twin.evaluation.temporal import cutoff_violations
from digital_twin.evaluation.missingness import classify
from digital_twin.evaluation.workflow import assert_separation

def test_metadata_and_append_version(tmp_path):
 m=ResultMetadata.create("e1",dataset_version="d",presentation_id="p",data_origin="empirical")
 path=append_rows(tmp_path/"r.csv",[{**m.__dict__,"value":1}]); second=append_rows(path,[{"value":2}])
 assert path.exists() and second != path

def test_metrics_and_split_deterministic():
 assert binary_metrics([0,1],[.1,.9])["f1"] == 1.0
 assert deterministic_split(range(20)) == deterministic_split(range(20))

def test_cutoff_and_missingness():
 assert cutoff_violations([{"checkpoint_time":3,"features":[{"source_time":4,"source":"future"}]}])
 assert classify(0) == "observed_zero"
 assert classify(0, observed=False) == "missing"
 assert classify(None, due=False) == "not_due"

def test_workflow_state_is_immutable():
 before={"prediction":1,"evidence":2,"support_case":3,"support_action":4}
 assert_separation(before, dict(before))
