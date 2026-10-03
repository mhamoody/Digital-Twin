from __future__ import annotations
import csv, hashlib, os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
SEEDS=(42,123,2026)
@dataclass(frozen=True)
class ResultMetadata:
    experiment_id:str; git_commit:str; dataset_version:str; presentation_id:str; checkpoint:int|None; model_name:str; model_version:str; policy_version:str|None; seed:int; data_origin:str; run_timestamp:str
    @classmethod
    def create(cls, experiment_id:str, **kwargs:Any):
        v=dict(git_commit=os.getenv('GIT_COMMIT','unknown'),dataset_version='unknown',presentation_id='unknown',checkpoint=None,model_name='unknown',model_version='unknown',policy_version=None,seed=42,data_origin='unknown',run_timestamp=datetime.now(timezone.utc).isoformat());v.update(kwargs);return cls(experiment_id,**v)
def result_row(metadata:ResultMetadata,**values):return {**asdict(metadata),**values}
def append_rows(path:str|Path,rows:Iterable[dict]):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);rows=list(rows)
    if p.exists() and p.stat().st_size:p=p.with_name(f'{p.stem}.{hashlib.sha256(p.read_bytes()).hexdigest()[:10]}{p.suffix}')
    if rows:
        with p.open('w',newline='',encoding='utf-8') as h:
            w=csv.DictWriter(h,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    return p
