"""Source adapters that normalize operational and empirical evidence."""

from .moodle import (
    MOODLE_ADAPTER_VERSION,
    ControlledExport,
    ControlledExportHeader,
    MappingBatch,
    MoodleControlledExportAdapter,
    MoodleWebServiceReader,
    ReplayWatermark,
    build_oulad_controlled_export,
)
from .replay import CONNECTOR_ID, replay_controlled_export

__all__ = [
    "MOODLE_ADAPTER_VERSION",
    "ControlledExport",
    "ControlledExportHeader",
    "MappingBatch",
    "MoodleControlledExportAdapter",
    "MoodleWebServiceReader",
    "ReplayWatermark",
    "build_oulad_controlled_export",
    "CONNECTOR_ID",
    "replay_controlled_export",
]
