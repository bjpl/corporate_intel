"""
Report Generation Job

Generates reports from analyzed data.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

from src.jobs.base import BaseJob, JobRegistry, JobResult

logger = logging.getLogger(__name__)


@JobRegistry.register("report_generation")
class ReportGenerationJob(BaseJob):
    """
    Generate reports from data

    Parameters:
        data: Data to include in report
        template: Report template name
        format: Output format (json, html, pdf)
        title: Report title
        sections: Sections to include
    """

    max_retries = 2
    retry_delay = 1.0
    timeout = 300.0

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute report generation"""
        data = kwargs.get("data", {})
        template = kwargs.get("template", "default")
        output_format = kwargs.get("format", "json")
        title = kwargs.get("title", "Data Report")
        sections = kwargs.get("sections", [])

        logger.info(f"Starting report generation: {title}")

        # Generate report
        report = {
            "title": title,
            "generated_at": datetime.utcnow().isoformat(),
            "template": template,
            "format": output_format,
            "sections": []
        }

        # Add sections
        if not sections:
            # Default section with all data
            report["sections"].append({
                "title": "Data Summary",
                "content": data
            })
        else:
            for section in sections:
                section_data = {
                    "title": section.get("title", "Untitled Section"),
                    "content": {}
                }

                # Extract data for section
                data_key = section.get("data_key")
                if data_key and data_key in data:
                    section_data["content"] = data[data_key]
                else:
                    section_data["content"] = data

                # Apply section formatting
                if section.get("format"):
                    section_data["format"] = section["format"]

                report["sections"].append(section_data)

        # Format report based on output format
        if output_format == "html":
            report["html"] = self._generate_html(report)
        elif output_format == "markdown":
            report["markdown"] = self._generate_markdown(report)

        logger.info(f"Report generation completed: {len(report['sections'])} sections")

        return {
            "report": report,
            "sections_count": len(report["sections"]),
            "format": output_format
        }

    def _generate_html(self, report: Dict[str, Any]) -> str:
        """Generate HTML report"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{report['title']}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                h2 {{ color: #666; border-bottom: 1px solid #ccc; }}
                .metadata {{ color: #999; font-size: 0.9em; }}
                .section {{ margin: 20px 0; }}
                pre {{ background: #f5f5f5; padding: 10px; overflow-x: auto; }}
            </style>
        </head>
        <body>
            <h1>{report['title']}</h1>
            <div class="metadata">Generated: {report['generated_at']}</div>
        """

        for section in report["sections"]:
            html += f"""
            <div class="section">
                <h2>{section['title']}</h2>
                <pre>{str(section['content'])}</pre>
            </div>
            """

        html += """
        </body>
        </html>
        """

        return html

    def _generate_markdown(self, report: Dict[str, Any]) -> str:
        """Generate Markdown report"""
        md = f"# {report['title']}\n\n"
        md += f"*Generated: {report['generated_at']}*\n\n"

        for section in report["sections"]:
            md += f"## {section['title']}\n\n"
            md += f"```\n{str(section['content'])}\n```\n\n"

        return md

    def on_start(self) -> None:
        """Called when job starts"""
        logger.info(f"Starting report generation job {self.job_id}")

    def on_success(self, result: JobResult) -> None:
        """Called on successful completion"""
        sections_count = result.data.get("sections_count", 0)
        logger.info(
            f"Report generation job {self.job_id} completed: "
            f"{sections_count} sections"
        )
