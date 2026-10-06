from __future__ import annotations
E2_V2_OUTPUT_SCHEMA={"type":"object","required":["assessment","claims","abstain"],"properties":{"assessment":{"type":"string"},"claims":{"type":"array","items":{"type":"object","required":["claim","evidence_ids"],"properties":{"claim":{"type":"string"},"evidence_ids":{"type":"array","items":{"type":"string"},"minItems":1}},"additionalProperties":False}},"abstain":{"type":"boolean"},"uncertainty_note":{"type":"string"}},"additionalProperties":False}
def schema():
 import copy
 return copy.deepcopy(E2_V2_OUTPUT_SCHEMA)
