import os
import json

def load_config():
    """
    Load dummy-scan rules used to compute DISCARD_FRAMES.

    Preferred path:
      configuration_templates/dummy_scan_settings.json

    Backward-compatible fallback:
      configuration_templates/motion_outlier_settings.json
      (if it contains dummy_scan_rules/default_dummy)
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(script_dir, "..", "configuration_templates")

    preferred = os.path.join(template_dir, "dummy_scan_settings.json")
    legacy = os.path.join(template_dir, "motion_outlier_settings.json")

    default_cfg = {"dummy_scan_rules": [], "default_dummy": 2}

    if os.path.exists(preferred):
        with open(preferred, "r") as f:
            cfg = json.load(f)
        # Ensure required keys exist.
        cfg.setdefault("dummy_scan_rules", [])
        cfg.setdefault("default_dummy", 2)
        return cfg

    if os.path.exists(legacy):
        with open(legacy, "r") as f:
            cfg = json.load(f)
        # Some legacy configs are motion-outlier-only; only use dummy keys if present.
        if "dummy_scan_rules" in cfg or "default_dummy" in cfg:
            cfg.setdefault("dummy_scan_rules", [])
            cfg.setdefault("default_dummy", 2)
            return cfg

    print(
        f"Dummy scan configuration not found. Looked for: {preferred} and {legacy}. Using defaults."
    )
    return default_cfg

def get_dummy_scans(num_frames, config):
    """
    Determine the number of dummy scans based on the number of frames.
    Looks for an exact match in the dummy_scan_rules; if none is found, returns default_dummy.
    """
    for rule in config.get("dummy_scan_rules", []):
        if rule.get("frames") == num_frames:
            return rule.get("dummy", config.get("default_dummy", 2))
    return config.get("default_dummy", 2)
