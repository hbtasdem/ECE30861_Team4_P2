# fetch_metadata.py
import json

def fetch_multiple_configs(model_urls, get_model_config_fn, output_file='model_configs.json'):
    """Fetch configs for multiple models and save to file.
    - model_urls: list of model URLs
    - get_model_config_fn: function that takes model_url -> config dict
    """
    all_configs = {}

    for model_url in model_urls:
        model_config = get_model_config_fn(model_url)
        if model_config:
            model_id = (
                model_config.get("id")
                or model_config.get("modelId")
                or model_url.split("/")[-1]
            )
            all_configs[model_id] = model_config
            print(f"✓ Fetched config for {model_id}")
        else:
            print(f"✗ No config found for {model_url}")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_configs, f, indent=2, ensure_ascii=False)

    print(f"\nExported {len(all_configs)} model configs to '{output_file}'")
    return all_configs
