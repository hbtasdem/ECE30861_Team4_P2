# Before setting up the actual dabase backend, use this as an example database access

# Format:
# artifacts_db[artifact_id] = {
#     "metadata" : {
#         "name" : name we parse from url,
#         "id" : id assigned during ingest,
#         "type": Enum[model, dataset, code]
#     },
#     "data": {
#         "url" : url from ingest
#     },
#     "rating" : json object from metrics calculation
# }

from typing import Any, Dict

artifacts_db: Dict[str, Dict[str, Any]] = {
    "1234567890": {
        "metadata": {
            "name": "bert-base-uncased",
            "id": 1234567890,
            "type": "MODEL"
        },
        "data": {
            "url": "https://github.com/google-research/bert"
        },
        "rating": {
            "name": "bert-base-uncased",
            "category": "MODEL",
            "net_score": 0.95,
            "net_score_latency": 180,
            "ramp_up_time": 0.90,
            "ramp_up_time_latency": 45,
            "bus_factor": 0.95,
            "bus_factor_latency": 25,
            "performance_claims": 0.92,
            "performance_claims_latency": 35,
            "license": 1.00,
            "license_latency": 10,
            "size_score": {"raspberry_pi": 0.20, "jetson_nano": 0.40, "desktop_pc": 0.95, "aws_server": 1.00},
            "size_score_latency": 50,
            "dataset_and_code_score": 1.00,
            "dataset_and_code_score_latency": 15,
            "dataset_quality": 0.95,
            "dataset_quality_latency": 20,
            "code_quality": 0.93,
            "code_quality_latency": 22}
    }
}
