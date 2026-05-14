from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))
from _placeholder_common import parse_args, write_json, write_metrics, write_text


args = parse_args()
outputs = Path(args.outputs_dir)
write_text(outputs, "tables/differential_genes.tsv", "gene_id\tlog2_fold_change\tadjusted_p_value\nplaceholder_gene\t0.0\t1.0\n")
write_json(outputs, "figures/volcano_plot_spec.json", {"chart": "volcano", "source": "local_placeholder"})
write_text(outputs, "notes/method_note.md", "# Method Note\n\nLocal placeholder differential expression output.\n")
write_text(outputs, "notes/risk_notes.md", "# Risk Notes\n\nBatch, sample size, and FDR require review.\n")
write_metrics(outputs, "transcriptomics.differential_expression")
print("transcriptomics.differential_expression placeholder completed")
