"""Metrics collection and reporting for invoice processing."""

import json
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional
from enum import Enum


class ProcessingStatus(str, Enum):
    """Invoice processing status."""
    SUCCESS = "success"
    REJECTED = "rejected"
    REQUIRES_REVIEW = "requires_review"
    FAILED = "failed"


@dataclass
class AgentMetrics:
    """Metrics for a single agent execution."""
    agent_name: str
    start_time: float
    end_time: float
    duration_ms: float
    status: str = "success"
    error: Optional[str] = None

    @property
    def duration_seconds(self) -> float:
        """Duration in seconds."""
        return self.duration_ms / 1000.0


@dataclass
class InvoiceMetrics:
    """Metrics for a complete invoice processing."""
    invoice_number: str
    vendor: str
    amount: float
    status: ProcessingStatus
    start_time: datetime
    end_time: datetime
    total_duration_ms: float
    ingestion_ms: float
    validation_ms: float
    approval_ms: float
    payment_ms: float
    approval_confidence: float = 0.0
    validation_issues: int = 0
    error: Optional[str] = None

    @property
    def total_duration_seconds(self) -> float:
        """Total duration in seconds."""
        return self.total_duration_ms / 1000.0

    @property
    def successful(self) -> bool:
        """Whether processing was successful."""
        return self.status == ProcessingStatus.SUCCESS

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['start_time'] = self.start_time.isoformat()
        data['end_time'] = self.end_time.isoformat()
        data['status'] = self.status.value
        return data


class MetricsCollector:
    """Collect and report metrics for invoice processing."""

    def __init__(self, output_dir: Path = Path("metrics")):
        """
        Initialize metrics collector.

        Args:
            output_dir: Directory to write metrics files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.metrics: list[InvoiceMetrics] = []
        self._agent_timers: dict[str, float] = {}

    def start_agent_timer(self, agent_name: str) -> None:
        """Start timing an agent."""
        self._agent_timers[agent_name] = time.time()

    def end_agent_timer(self, agent_name: str) -> float:
        """End timing an agent and return duration in milliseconds."""
        if agent_name not in self._agent_timers:
            return 0.0
        start = self._agent_timers.pop(agent_name)
        duration_ms = (time.time() - start) * 1000
        return duration_ms

    def record_invoice(self, metrics: InvoiceMetrics) -> None:
        """Record metrics for a processed invoice."""
        self.metrics.append(metrics)

    def get_summary(self) -> dict:
        """Get summary statistics."""
        if not self.metrics:
            return {}

        total = len(self.metrics)
        successful = sum(1 for m in self.metrics if m.successful)
        rejected = sum(1 for m in self.metrics if m.status == ProcessingStatus.REJECTED)
        requires_review = sum(1 for m in self.metrics if m.status == ProcessingStatus.REQUIRES_REVIEW)
        failed = sum(1 for m in self.metrics if m.status == ProcessingStatus.FAILED)

        durations = [m.total_duration_seconds for m in self.metrics]
        amounts = [m.amount for m in self.metrics if m.amount > 0]
        confidences = [m.approval_confidence for m in self.metrics if m.approval_confidence > 0]

        return {
            "total_invoices": total,
            "successful": successful,
            "successful_rate": f"{100 * successful / total:.1f}%",
            "rejected": rejected,
            "rejected_rate": f"{100 * rejected / total:.1f}%",
            "requires_review": requires_review,
            "review_rate": f"{100 * requires_review / total:.1f}%",
            "failed": failed,
            "failed_rate": f"{100 * failed / total:.1f}%",
            "latency": {
                "mean_seconds": f"{sum(durations) / len(durations):.2f}",
                "min_seconds": f"{min(durations):.2f}",
                "max_seconds": f"{max(durations):.2f}",
                "p95_seconds": f"{sorted(durations)[int(0.95 * len(durations))]:.2f}" if len(durations) > 1 else "N/A",
            },
            "amounts": {
                "total": f"${sum(amounts):.2f}",
                "mean": f"${sum(amounts) / len(amounts):.2f}" if amounts else "$0.00",
                "min": f"${min(amounts):.2f}" if amounts else "$0.00",
                "max": f"${max(amounts):.2f}" if amounts else "$0.00",
            },
            "confidence": {
                "mean": f"{sum(confidences) / len(confidences):.2f}" if confidences else "N/A",
                "min": f"{min(confidences):.2f}" if confidences else "N/A",
                "max": f"{max(confidences):.2f}" if confidences else "N/A",
            }
        }

    def export_json(self, filename: str = "metrics.json") -> Path:
        """Export metrics to JSON file."""
        output_path = self.output_dir / filename
        data = [m.to_dict() for m in self.metrics]
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        return output_path

    def export_csv(self, filename: str = "metrics.csv") -> Path:
        """Export metrics to CSV file."""
        import csv
        output_path = self.output_dir / filename

        if not self.metrics:
            return output_path

        fieldnames = [
            'invoice_number', 'vendor', 'amount', 'status', 'total_duration_ms',
            'ingestion_ms', 'validation_ms', 'approval_ms', 'payment_ms',
            'approval_confidence', 'validation_issues', 'error'
        ]

        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for metric in self.metrics:
                writer.writerow({
                    'invoice_number': metric.invoice_number,
                    'vendor': metric.vendor,
                    'amount': metric.amount,
                    'status': metric.status.value,
                    'total_duration_ms': f"{metric.total_duration_ms:.1f}",
                    'ingestion_ms': f"{metric.ingestion_ms:.1f}",
                    'validation_ms': f"{metric.validation_ms:.1f}",
                    'approval_ms': f"{metric.approval_ms:.1f}",
                    'payment_ms': f"{metric.payment_ms:.1f}",
                    'approval_confidence': f"{metric.approval_confidence:.2f}",
                    'validation_issues': metric.validation_issues,
                    'error': metric.error or ""
                })
        return output_path

    def print_summary(self) -> None:
        """Print summary to console."""
        summary = self.get_summary()

        if not summary:
            print("No metrics collected.")
            return

        print("\n" + "="*80)
        print("METRICS SUMMARY")
        print("="*80)

        print(f"\nTOTAL INVOICES: {summary['total_invoices']}")
        print(f"  ✓ Successful:      {summary['successful']} ({summary['successful_rate']})")
        print(f"  ✗ Rejected:        {summary['rejected']} ({summary['rejected_rate']})")
        print(f"  ⚠ Requires Review: {summary['requires_review']} ({summary['review_rate']})")
        print(f"  ⚡ Failed:         {summary['failed']} ({summary['failed_rate']})")

        print(f"\nLATENCY (per invoice):")
        print(f"  Mean:   {summary['latency']['mean_seconds']}s")
        print(f"  Min:    {summary['latency']['min_seconds']}s")
        print(f"  Max:    {summary['latency']['max_seconds']}s")
        print(f"  P95:    {summary['latency']['p95_seconds']}s")

        print(f"\nAMOUNTS (USD):")
        print(f"  Total:  {summary['amounts']['total']}")
        print(f"  Mean:   {summary['amounts']['mean']}")
        print(f"  Range:  {summary['amounts']['min']} - {summary['amounts']['max']}")

        print(f"\nAPPROVAL CONFIDENCE:")
        print(f"  Mean:   {summary['confidence']['mean']}")
        print(f"  Range:  {summary['confidence']['min']} - {summary['confidence']['max']}")

        print("\n" + "="*80)
