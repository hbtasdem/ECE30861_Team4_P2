from typing import Dict, Literal, TypedDict


class ProjectMetadata(TypedDict):
    name: str
    category: Literal["MODEL", "DATASET", "CODE"]

    net_score: float
    net_score_latency: int

    ramp_up_time: float
    ramp_up_time_latency: int

    bus_factor: float
    bus_factor_latency: int

    performance_claims: float
    performance_claims_latency: int

    license: float
    license_latency: int

    size_score: Dict[str, float]  # {"raspberry_pi": 0.8, ... }
    size_score_latency: int

    dataset_and_code_score: float
    dataset_and_code_score_latency: int

    dataset_quality: float
    dataset_quality_latency: int

    code_quality: float
    code_quality_latency: int
