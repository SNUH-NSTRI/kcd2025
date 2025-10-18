"""
Comprehensive Report Generator Plugin

This plugin generates detailed research reports that integrate:
1. Original research question from the user
2. NCT clinical trial literature and papers
3. Statistical analysis results from the Statistician agent
4. Treatment outcomes and insights
"""

from __future__ import annotations

import datetime as dt
import json
import logging
from pathlib import Path
from typing import Any

from ..context import PipelineContext
from .. import models

logger = logging.getLogger(__name__)


class ComprehensiveReportGenerator:
    """
    Generate comprehensive research reports integrating multiple data sources.

    This generator combines:
    - User's research question
    - Clinical trial literature from corpus
    - Statistical analysis (PSM, survival, causal forest)
    - Treatment outcomes and recommendations
    """

    def run(
        self,
        params: models.WriteReportParams,
        ctx: PipelineContext,
        analysis: models.AnalysisMetrics,
    ) -> models.ReportBundle:
        """
        Generate comprehensive report.

        Args:
            params: Report generation parameters
            ctx: Pipeline context with project paths
            analysis: Analysis results from statistician

        Returns:
            ReportBundle with complete report and figures
        """
        logger.info(f"Generating comprehensive report for {ctx.project_id}")

        # Load all required data sources
        research_question = self._load_research_question(ctx)
        literature = self._load_literature(ctx)
        statistician_report = self._load_statistician_report(ctx)
        trial_schema = self._load_trial_schema(ctx)

        # Generate report sections
        report_body = self._generate_report(
            ctx=ctx,
            research_question=research_question,
            literature=literature,
            statistician_report=statistician_report,
            trial_schema=trial_schema,
            analysis=analysis,
        )

        # Generate figures (placeholder for now)
        figures = self._generate_figures(analysis)

        return models.ReportBundle(
            schema_version="report.v1",
            report_body=report_body,
            figures=figures,
            extra_files=None,
        )

    def _load_research_question(self, ctx: PipelineContext) -> str:
        """Load user's research question from project metadata."""
        try:
            metadata_path = Path(ctx.workspace) / ctx.project_id / "metadata.json"
            if metadata_path.exists():
                with open(metadata_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                    return metadata.get("research_question", "No research question provided")
            return "No research question provided"
        except Exception as e:
            logger.warning(f"Failed to load research question: {e}")
            return "No research question provided"

    def _load_literature(self, ctx: PipelineContext) -> dict[str, Any]:
        """Load clinical trial literature from corpus."""
        try:
            lit_path = Path(ctx.workspace) / ctx.project_id / "lit" / "corpus.json"
            if lit_path.exists():
                with open(lit_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            return {"documents": []}
        except Exception as e:
            logger.warning(f"Failed to load literature: {e}")
            return {"documents": []}

    def _load_statistician_report(self, ctx: PipelineContext) -> str:
        """Load statistician's analysis report if available."""
        try:
            # Find the statistician report in cohort outputs
            cohorts_path = Path(ctx.workspace) / ctx.project_id / "cohorts"
            if cohorts_path.exists():
                # Look for statistician_report.md in any cohort subdirectory
                for cohort_dir in cohorts_path.iterdir():
                    if cohort_dir.is_dir():
                        report_path = cohort_dir / "outputs" / "statistician_report.md"
                        if report_path.exists():
                            return report_path.read_text(encoding="utf-8")
            return ""
        except Exception as e:
            logger.warning(f"Failed to load statistician report: {e}")
            return ""

    def _load_trial_schema(self, ctx: PipelineContext) -> dict[str, Any]:
        """Load trial schema with inclusion/exclusion criteria."""
        try:
            schema_path = Path(ctx.workspace) / ctx.project_id / "schema" / "schema.json"
            if schema_path.exists():
                with open(schema_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.warning(f"Failed to load trial schema: {e}")
            return {}

    def _generate_report(
        self,
        ctx: PipelineContext,
        research_question: str,
        literature: dict[str, Any],
        statistician_report: str,
        trial_schema: dict[str, Any],
        analysis: models.AnalysisMetrics,
    ) -> str:
        """Generate the complete report markdown."""

        now_iso = dt.datetime.now(dt.timezone.utc).isoformat()

        sections = []

        # Title and metadata
        sections.append(f"# Clinical Trial Emulation Report")
        sections.append(f"\n**Project ID:** {ctx.project_id}")
        sections.append(f"**Generated:** {now_iso}")
        sections.append(f"\n---\n")

        # 1. Research Question Section
        sections.append("## 1. Research Question")
        sections.append(f"\n{research_question}\n")

        # 2. Clinical Trial Context
        sections.append("## 2. Clinical Trial Context")
        docs = literature.get("documents", [])
        if docs:
            for doc in docs:
                title = doc.get("title", "Untitled Study")
                sections.append(f"\n### {title}")

                metadata = doc.get("metadata", {})
                nct_id = metadata.get("nctId", "Unknown")
                sections.append(f"\n**NCT ID:** {nct_id}")

                # Eligibility criteria
                eligibility = metadata.get("eligibility", {})
                criteria = eligibility.get("eligibilityCriteria", "")
                if criteria:
                    sections.append(f"\n**Eligibility Criteria:**\n```\n{criteria}\n```")

                # Study design
                design = metadata.get("design", {})
                phases = design.get("phases", [])
                if phases:
                    sections.append(f"\n**Study Phase:** {', '.join(phases)}")

                # Sponsors
                sponsors = metadata.get("sponsors", {})
                lead_sponsor = sponsors.get("leadSponsor", {})
                sponsor_name = lead_sponsor.get("name", "")
                if sponsor_name:
                    sections.append(f"**Lead Sponsor:** {sponsor_name}")
        else:
            sections.append("\nNo clinical trial literature available.")

        # 3. Trial Schema
        if trial_schema:
            sections.append("\n## 3. Trial Design")

            # Inclusion criteria
            inclusion = trial_schema.get("inclusion", [])
            if inclusion:
                sections.append("\n### Inclusion Criteria")
                for idx, criteria in enumerate(inclusion, 1):
                    desc = criteria.get("description", "")
                    sections.append(f"{idx}. {desc}")

            # Exclusion criteria
            exclusion = trial_schema.get("exclusion", [])
            if exclusion:
                sections.append("\n### Exclusion Criteria")
                for idx, criteria in enumerate(exclusion, 1):
                    desc = criteria.get("description", "")
                    sections.append(f"{idx}. {desc}")

        # 4. Statistical Analysis Results
        if statistician_report:
            sections.append("\n## 4. Statistical Analysis")
            sections.append("\nDetailed statistical analysis performed by the Statistician Agent:\n")
            sections.append(statistician_report)
        else:
            sections.append("\n## 4. Statistical Analysis")
            sections.append("\nStatistical analysis is in progress or not yet available.")

        # 5. Treatment Outcomes Summary
        sections.append("\n## 5. Treatment Outcomes")

        outcomes = list(analysis.outcomes)
        if outcomes:
            sections.append(f"\n**Total Subjects Analyzed:** {len(outcomes)}")

            # Calculate summary statistics
            treatment_count = sum(1 for o in outcomes if getattr(o, 'treatment', False))
            control_count = len(outcomes) - treatment_count

            sections.append(f"- Treatment Group: {treatment_count}")
            sections.append(f"- Control Group: {control_count}")

            # Sample outcomes table
            sections.append("\n### Sample Outcomes (First 10 Subjects)")
            sections.append("\n| Subject ID | Treatment | Propensity | CATE | Predicted Outcome |")
            sections.append("|-----------|-----------|------------|------|-------------------|")

            for outcome in outcomes[:10]:
                subject_id = getattr(outcome, 'subject_id', 'N/A')
                treatment = getattr(outcome, 'treatment', False)
                propensity = getattr(outcome, 'propensity', 0.0)
                ate = getattr(outcome, 'ate', 0.0)
                predicted = getattr(outcome, 'predicted_outcome', 0.0)

                treatment_str = "Yes" if treatment else "No"
                sections.append(
                    f"| {subject_id} | {treatment_str} | {propensity:.3f} | "
                    f"{ate:.3f} | {predicted:.3f} |"
                )
        else:
            sections.append("\nNo outcome data available.")

        # 6. Analysis Metrics
        sections.append("\n## 6. Key Metrics")
        metrics = analysis.metrics
        if metrics:
            sections.append("\n```json")
            sections.append(json.dumps(metrics, indent=2))
            sections.append("```")

        # 7. Conclusions and Recommendations
        sections.append("\n## 7. Conclusions")
        sections.append("\n### Summary of Findings")
        sections.append(
            "\nBased on the integrated analysis of clinical trial data, "
            "real-world evidence, and statistical modeling, the following "
            "conclusions can be drawn:"
        )
        sections.append(
            "\n1. **Treatment Effect:** Review the hazard ratios and confidence "
            "intervals in the statistical analysis section."
        )
        sections.append(
            "\n2. **Patient Selection:** Consider the eligibility criteria and "
            "cohort characteristics when interpreting results."
        )
        sections.append(
            "\n3. **Clinical Implications:** Evaluate the clinical significance "
            "alongside statistical significance."
        )

        sections.append("\n### Recommendations")
        sections.append("\n- Review the detailed statistician report for methodology")
        sections.append("- Consider heterogeneous treatment effects by subgroup")
        sections.append("- Validate findings with additional sensitivity analyses")
        sections.append("- Consult with clinical experts before making treatment decisions")

        # 8. Methodology Notes
        sections.append("\n## 8. Methodology")
        sections.append("\nThis report was generated using:")
        sections.append("- **Propensity Score Matching (PSM)** for covariate balance")
        sections.append("- **Cox Proportional Hazards** for survival analysis")
        sections.append("- **Causal Forest** for heterogeneous treatment effects")
        sections.append("- **Real-world data** from electronic health records")

        # Footer
        sections.append("\n---")
        sections.append("\n*This report was automatically generated by the RWE Clinical Trial Emulation Platform.*")

        return "\n".join(sections)

    def _generate_figures(self, analysis: models.AnalysisMetrics) -> list[models.FigureArtifact]:
        """Generate report figures (placeholder for now)."""

        # Placeholder 1x1 PNG
        placeholder_png = (
            b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwADjgF/qSb9lQAAAABJRU5ErkJggg=="
        )

        return [
            models.FigureArtifact(
                name="outcome-distribution",
                description="Treatment outcome distribution across cohort",
                data=placeholder_png,
                media_type="image/png",
            )
        ]


__all__ = ["ComprehensiveReportGenerator"]
