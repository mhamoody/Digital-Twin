# Protocol freeze requirements

Freeze the dataset version, checkpoint selection, prompt/model identity, split, and seeds 42, 123, and 2026 before execution. The final test partition is never used for threshold selection or calibration. Development grounding cases must remain labelled `development`; held-out cases require a separate frozen manifest.
