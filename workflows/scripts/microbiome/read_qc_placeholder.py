from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))
from _placeholder_common import parse_args, write_json, write_metrics, write_text


args = parse_args()
outputs = Path(args.outputs_dir)
write_text(outputs, "tables/qc_summary.tsv", "metric\tvalue\nsamples_reviewed\tplaceholder\n")
write_json(outputs, "figures/read_quality_chart_spec.json", {"chart": "read_quality", "source": "local_placeholder"})
write_text(outputs, "notes/method_note.md", "# Method Note\n\nLocal placeholder microbiome QC output.\n")
write_text(outputs, "notes/risk_notes.md", "# Risk Notes\n\nFiltering requires review.\n")
write_metrics(outputs, "microbiome.read_qc")
print("microbiome.read_qc placeholder completed")
