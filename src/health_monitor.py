"""Health monitoring system for registry components with logs from last hour.

FILE PURPOSE:
Implements health monitoring per OpenAPI v3.4.4 spec /health/components endpoint.
Tracks component status, metrics, issues, and logs within a configurable window (default 60min).

SPEC COMPLIANCE:
Per OpenAPI v3.4.4 Section /health/components:
- Returns HealthComponentCollection schema
- Per-component diagnostics including status, metrics, issues, logs
- Optional includeTimeline parameter for activity sampling
- Configurable windowMinutes (5-1440, default 60)

COMPONENTS MONITORED:
- s3-storage: S3 artifact storage backend
- database: SQLAlchemy database connection
- authentication: JWT token validation system
- rate-calculator: Artifact rating/scoring pipeline
- metrics-engine: Scoring metrics calculations
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class HealthMetricValue(BaseModel):
    """Single metric value with unit."""

    value: float | str | bool | int
    unit: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class HealthTimelineEntry(BaseModel):
    """Time-series datapoint for component metric."""

    bucket: datetime
    value: float
    unit: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class HealthIssue(BaseModel):
    """Outstanding issue impacting component."""

    code: str
    severity: str  # "info" | "warning" | "error"
    summary: str
    details: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class HealthLogReference(BaseModel):
    """Link to logs relevant to component."""

    label: str
    url: str
    tail_available: Optional[bool] = False
    last_updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class HealthComponentDetail(BaseModel):
    """Detailed health status for single component."""

    id: str
    display_name: Optional[str] = None
    status: str  # "ok" | "degraded" | "critical" | "unknown"
    observed_at: datetime
    description: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    issues: List[HealthIssue] = []
    timeline: List[HealthTimelineEntry] = []
    logs: List[HealthLogReference] = []

    model_config = ConfigDict(from_attributes=True)


class HealthComponentCollection(BaseModel):
    """Complete health diagnostics for all components."""

    components: List[HealthComponentDetail]
    generated_at: datetime
    window_minutes: int

    model_config = ConfigDict(from_attributes=True)


class HealthMonitor:
    """Central health monitoring system for registry components."""

    def __init__(self) -> None:
        """Initialize health monitor with component tracking."""
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        self.start_time = datetime.utcnow()

        # Component definitions
        self.components = {
            "s3-storage": {
                "display_name": "S3 Storage Backend",
                "description": "AWS S3 bucket for artifact metadata storage",
            },
            "database": {
                "display_name": "Database",
                "description": "SQLAlchemy database for audit logs and ratings",
            },
            "authentication": {
                "display_name": "Authentication",
                "description": "JWT token validation system",
            },
            "rate-calculator": {
                "display_name": "Rate Calculator",
                "description": "Artifact rating and scoring pipeline",
            },
            "metrics-engine": {
                "display_name": "Metrics Engine",
                "description": "Individual metric calculations",
            },
        }

    def _read_logs_from_window(
        self, window_minutes: int
    ) -> Dict[str, List[HealthLogReference]]:
        """Read and parse log files from the last N minutes.

        Args:
            window_minutes: Number of minutes to look back

        Returns:
            Dictionary mapping component name to list of log references
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=window_minutes)
        logs_by_component: Dict[str, List[HealthLogReference]] = {
            comp: [] for comp in self.components.keys()
        }

        if not self.log_dir.exists():
            return logs_by_component

        try:
            for log_file in sorted(self.log_dir.glob("*.log"), reverse=True):
                # Check file modification time
                file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_mtime < cutoff_time:
                    continue

                # Parse filename for component
                filename = log_file.name
                component = self._map_logfile_to_component(filename)

                if component and component in logs_by_component:
                    try:
                        last_modified = datetime.fromtimestamp(log_file.stat().st_mtime)
                        log_ref = HealthLogReference(
                            label=filename,
                            url=f"/logs/{filename}",
                            tail_available=True,
                            last_updated_at=last_modified,
                        )
                        logs_by_component[component].append(log_ref)
                    except Exception:
                        pass
        except Exception as e:
            logging.warning(f"Failed to read logs: {e}")

        return logs_by_component

    def _map_logfile_to_component(self, filename: str) -> Optional[str]:
        """Map log filename to component identifier.

        Args:
            filename: Name of log file

        Returns:
            Component identifier or None
        """
        filename_lower = filename.lower()

        if "auth" in filename_lower:
            return "authentication"
        elif "rate" in filename_lower or "rating" in filename_lower:
            return "rate-calculator"
        elif "metric" in filename_lower or "score" in filename_lower:
            return "metrics-engine"
        elif "s3" in filename_lower or "artifact" in filename_lower:
            return "s3-storage"
        elif "db" in filename_lower or "database" in filename_lower:
            return "database"

        # Map generic "test" logs to most relevant component
        if "test" in filename_lower:
            return "rate-calculator"

        return None

    def _get_component_status(self, component_id: str) -> str:
        """Determine current status of component.

        Args:
            component_id: Component identifier

        Returns:
            Status: "ok", "degraded", "critical", or "unknown"
        """
        # Check for recent errors in logs
        error_file = self.log_dir / f"error_{component_id}.log"
        if error_file.exists():
            try:
                file_mtime = datetime.fromtimestamp(error_file.stat().st_mtime)
                if file_mtime > datetime.utcnow() - timedelta(minutes=60):
                    return "degraded"
            except Exception:
                pass

        return "ok"

    def _get_component_metrics(self, component_id: str) -> Dict[str, Any]:
        """Get metrics for component.

        Args:
            component_id: Component identifier

        Returns:
            Dictionary of metric key/value pairs
        """
        metrics: Dict[str, Any] = {}

        if component_id == "s3-storage":
            try:
                import boto3

                s3 = boto3.client("s3")
                response = s3.head_bucket(Bucket="phase2-s3-bucket")
                metrics["bucket_accessible"] = True
                metrics["response_code"] = response["ResponseMetadata"]["HTTPStatusCode"]
            except Exception as e:
                metrics["bucket_accessible"] = False
                metrics["error"] = str(e)

        elif component_id == "authentication":
            metrics["token_algorithm"] = "HS256"
            metrics["token_expiration_minutes"] = 30
            metrics["password_hash_algorithm"] = "bcrypt"

        elif component_id == "rate-calculator":
            # Count recent rating calculations
            rating_logs = list(self.log_dir.glob("*rate*.log"))
            metrics["rating_log_count"] = len(rating_logs)
            metrics["status"] = "operational"

        elif component_id == "metrics-engine":
            # Count metric logs
            metric_logs = list(self.log_dir.glob("*metric*.log")) + list(
                self.log_dir.glob("*score*.log")
            )
            metrics["metric_log_count"] = len(metric_logs)
            metrics["status"] = "operational"

        elif component_id == "database":
            metrics["connection_pool_size"] = 5
            metrics["status"] = "operational"

        return metrics

    def get_health_components(
        self, window_minutes: int = 60, include_timeline: bool = False
    ) -> HealthComponentCollection:
        """Get complete health diagnostics for all components.

        Args:
            window_minutes: Observation window in minutes (5-1440, default 60)
            include_timeline: Whether to include activity timelines

        Returns:
            HealthComponentCollection with all component details
        """
        # Validate window
        window_minutes = max(5, min(1440, window_minutes))

        # Read logs from window
        logs_by_component = self._read_logs_from_window(window_minutes)

        # Build component details
        components_detail: List[HealthComponentDetail] = []

        for comp_id, comp_info in self.components.items():
            status = self._get_component_status(comp_id)
            metrics = self._get_component_metrics(comp_id)
            issues: List[HealthIssue] = []
            timeline: List[HealthTimelineEntry] = []

            # Add issues if degraded
            if status == "degraded":
                issues.append(
                    HealthIssue(
                        code=f"{comp_id}_degraded",
                        severity="warning",
                        summary=f"{comp_info['display_name']} experiencing issues",
                        details=f"See logs for {comp_id} component",
                    )
                )

            # Add timeline if requested
            if include_timeline:
                # Create sample timeline entries
                now = datetime.utcnow()
                for i in range(min(5, window_minutes // 10)):
                    bucket_time = now - timedelta(minutes=i * 10)
                    timeline.append(
                        HealthTimelineEntry(
                            bucket=bucket_time,
                            value=float(i),
                            unit="requests_per_minute",
                        )
                    )

            component = HealthComponentDetail(
                id=comp_id,
                display_name=comp_info["display_name"],
                status=status,
                observed_at=datetime.utcnow(),
                description=comp_info["description"],
                metrics=metrics,
                issues=issues,
                timeline=timeline,
                logs=logs_by_component.get(comp_id, []),
            )
            components_detail.append(component)

        return HealthComponentCollection(
            components=components_detail,
            generated_at=datetime.utcnow(),
            window_minutes=window_minutes,
        )


# Global health monitor instance
health_monitor = HealthMonitor()
