"""Read-only source readers. Each module reads one kind of file and fails on its own."""
from . import event_log, ledger, reading_list, references, research_question, results_templates  # noqa: F401

# Every file the server reads, for /api/health and change detection.
WATCHED = (
    research_question.REL_PATH,
    references.REL_PATH,
    reading_list.REL_PATH,
    ledger.REL_PATH,
    *results_templates.REL_PATHS,
    event_log.REL_PATH,  # the dashboard's central log (external event files are imported into it)
)
