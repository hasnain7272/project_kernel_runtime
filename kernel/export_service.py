"""
Export Service for Research Reports.
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List
from .research import ResearchReport, ResearchSession

class ExportService:
    """Service to export research reports into MD, JSON, or PDF."""

    @staticmethod
    def to_markdown(report: ResearchReport, session: ResearchSession) -> str:
        """Convert a report to a Markdown string."""
        md = f"# Research Report: {session.query}\n\n"
        md += f"**Session ID:** {report.session_id}  \n"
        md += f"**Report ID:** {report.id}  \n"
        md += f"**Generated At:** {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}  \n\n"
        
        md += "## Summary\n"
        md += f"{report.summary}\n\n"
        
        if report.findings:
            md += "## Findings\n"
            for finding in report.findings:
                md += f"- **{finding.get('title', 'N/A')}:** {finding.get('description', '')}\n"
            md += "\n"
            
        md += "## Sources and Citations\n"
        for src in session.sources:
            md += f"- [{src.type}]({src.uri}) - Fetched at: {src.fetched_at.strftime('%Y-%m-%d %H:%M:%S') if src.fetched_at else 'N/A'}\n"
            
        return md

    @staticmethod
    def to_json(report: ResearchReport) -> str:
        """Convert a report to a JSON string."""
        return json.dumps(report.model_dump(), default=str, indent=2)

    @staticmethod
    def to_pdf(report: ResearchReport, session: ResearchSession, output_path: str):
        """
        Export to PDF. 
        Note: Requires fpdf2. If not installed, this will be a placeholder.
        """
        try:
            from fpdf import FPDF
            
            class PDF(FPDF):
                def header(self):
                    self.set_font('Arial', 'B', 15)
                    self.cell(80)
                    self.cell(30, 10, 'Research Report', 1, 0, 'C')
                    self.ln(20)

                def footer(self):
                    self.set_y(-15)
                    self.set_font('Arial', 'I', 8)
                    self.cell(0, 10, 'Page ' + str(self.page_no()) + '/{nb}', 0, 0, 'C')

            pdf = PDF()
            pdf.alias_nb_pages()
            pdf.add_page()
            pdf.set_font('Times', '', 12)
            
            pdf.cell(0, 10, f"Query: {session.query}", ln=True)
            pdf.cell(0, 10, f"Report ID: {report.id}", ln=True)
            pdf.ln(10)
            
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 10, "Summary", ln=True)
            pdf.set_font('Times', '', 12)
            pdf.multi_cell(0, 10, report.summary)
            pdf.ln(10)
            
            pdf.output(output_path)
            return output_path
        except ImportError:
            # Fallback if fpdf2 is not installed
            with open(output_path, "w") as f:
                f.write(ExportService.to_markdown(report, session))
            return output_path
