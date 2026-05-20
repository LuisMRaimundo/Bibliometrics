def test_dashboard_helpers_importable():
    """Dashboard helpers and import-safe shell."""
    import importlib

    from bibliometric_analysis.dashboard import compute_dashboard_metrics
    importlib.import_module("app_dashboard")
    assert callable(compute_dashboard_metrics)
