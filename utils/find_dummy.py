import os
import json

def load_config():
    """
    Load the JSON configuration file for motion outlier settings.
    The file is expected at configuration_templates/motion_outlier_settings.json
    relative to the project root (one level above the utils folder).
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "..", "configuration_templates", "motion_outlier_settings.json")
    if not os.path.exists(config_path):
        print(f"Configuration file not found: {config_path}. Using default settings.")
        return {"dummy_scan_rules": [], "default_dummy": 2}
    with open(config_path, 'r') as f:
        config = json.load(f)
    return config

def get_dummy_scans(num_frames, config):
    """
    Determine the number of dummy scans based on the number of frames.
    Looks for an exact match in the dummy_scan_rules; if none is found, returns default_dummy.
    """
    for rule in config.get("dummy_scan_rules", []):
        if rule.get("frames") == num_frames:
            return rule.get("dummy", config.get("default_dummy", 2))
    return config.get("default_dummy", 2)
