VARIANTS=('plain_llm','schema_only','evidence_first_full')
def grounding_row(**kwargs):
 d={'schema_valid':False,'evidence_valid':False,'unsupported_claim_count':0,'contradiction_count':0,'accepted':False,'abstained':False,'correction_required':False,'correction_success':False};d.update(kwargs);return d
