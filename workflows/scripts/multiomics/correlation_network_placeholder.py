from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))
from _placeholder_common import parse_args, write_json, write_metrics, write_text


args = parse_args()
outputs = Path(args.outputs_dir)
write_text(outputs, "tables/feature_associations.tsv", "source_feature\ttarget_feature\tassociation\tadjusted_p_value\nplaceholder_a\tplaceholder_b\t0.0\t1.0\n")
write_json(outputs, "figures/network_plot_spec.json", {"chart": "network", "source": "local_placeholder"})
write_text(outputs, "notes/method_note.md", "# Method Note\n\nLocal placeholder multi-omics network output.\n")
write_text(outputs, "notes/risk_notes.md", "# Risk Notes\n\nCorrelation is not causation.\n")
write_metrics(outputs, "multiomics.correlation_network")
print("multiomics.correlation_network placeholder completed")
