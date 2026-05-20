def test_streamlit_runner_import_safe():
    import importlib
    mod = importlib.import_module("streamlit_pipeline_runner")
    assert hasattr(mod, "main")
    assert callable(mod.main)
