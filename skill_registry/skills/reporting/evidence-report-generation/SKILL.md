# Evidence report generation

## Purpose
Standardize evidence question generation, evidence labels, review checklists, and draft report paragraphs from analysis results.

## Use when
Use this skill after statistical outputs are available and the user needs literature search questions, evidence tags, or a report draft scaffold.

## Inputs
- analysis_result_table
- method_note
- risk_notes

## Outputs
- literature_search_questions
- evidence_labels
- report_draft
- review_checklist

## Primary tools
- literature database query planning
- evidence grading rubric
- report template

## Default strategy
Convert analysis findings into traceable evidence questions, assign evidence-level labels, preserve methodological caveats, and mark all claims that require expert review.

## Parameters
- evidence_scope
- target_audience
- evidence_level_rubric
- review_status
- citation_policy

## QC checks
- Confirm each report claim links back to an analysis result.
- Confirm each claim has an evidence level and review status.
- Separate statistical association, literature support, and mechanistic claims.
- Preserve method and risk notes in the report scaffold.

## Interpretation limits
Literature relevance does not prove mechanism. Report drafts are not final scientific conclusions without expert review.

## Risk notes
Evidence labels can be overinterpreted. Claims must identify evidence grade, citation status, and whether expert review is complete.

## Next skills
No downstream skill is registered in phase one.

## Review requirement
Expert review is required before report release or external communication.
