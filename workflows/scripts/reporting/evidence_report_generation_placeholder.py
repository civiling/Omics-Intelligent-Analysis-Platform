from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))
from _placeholder_common import parse_args, write_metrics, write_text


args = parse_args()
outputs = Path(args.outputs_dir)
write_text(outputs, "tables/evidence_queries.tsv", "result_id\tquery\tevidence_level\nplaceholder_result\tplaceholder query\tpending_review\n")
write_text(outputs, "notes/report_draft.md", "# Report Draft\n\nLocal placeholder report draft.\n")
write_text(outputs, "notes/evidence_notes.md", "# Evidence Notes\n\nEvidence requires citation verification.\n")
write_text(outputs, "notes/risk_notes.md", "# Risk Notes\n\nLiterature relevance does not prove mechanism.\n")
write_metrics(outputs, "reporting.evidence_report_generation")
print("reporting.evidence_report_generation placeholder completed")
