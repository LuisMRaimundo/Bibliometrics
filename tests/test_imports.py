import importlib
import sys
import types

MODULE_NAME = "software_gui_pro_4"

def _install_dummy_compute_ppx():
    """
    Injeta um pacote falso 'metrics.percentiles' com a função compute_ppx,
    para que o import 'from metrics.percentiles import compute_ppx' funcione.
    """
    # metrics (package)
    metrics_pkg = types.ModuleType("metrics")
    metrics_pkg.__path__ = []  # marca como pacote
    sys.modules["metrics"] = metrics_pkg

    # metrics.percentiles (submodule)
    percentiles_mod = types.ModuleType("metrics.percentiles")
    def compute_ppx(df, col, by, p, ties):
        # devolve um DataFrame mínimo com colunas esperadas no teu uso
        # (lista(by) + ["ppx_threshold"])
        import pandas as pd
        out = (
            pd.DataFrame(df[by].drop_duplicates())
            .assign(ppx_threshold=0.0)
        )
        return out
    percentiles_mod.compute_ppx = compute_ppx
    sys.modules["metrics.percentiles"] = percentiles_mod

def _purge_module(name):
    for k in list(sys.modules.keys()):
        if k == name or k.startswith(name + "."):
            sys.modules.pop(k, None)

def test_imports_with_dummy_compute_ppx_and_real_optionals():
    """
    Smoke test: garante que o módulo carrega quando compute_ppx existe.
    Não força presença/ausência de opcionais; apenas observa valores.
    """
    _install_dummy_compute_ppx()
    _purge_module(MODULE_NAME)

    mod = importlib.import_module(MODULE_NAME)

    # compute_ppx deve estar importado
    assert hasattr(mod, "compute_ppx")

    # Flags/variáveis para opcionais existem (podem ser None/False se não instalados)
    assert hasattr(mod, "HAS_PYVIS")     # True se pyvis disponível; False caso contrário
    assert hasattr(mod, "community_louvain")  # None se não instalado
    assert hasattr(mod, "ig") and hasattr(mod, "leidenalg")  # None se não instalados

    # Regex de DOI tem grupo de captura (como no comentário do código)
    assert hasattr(mod, "doi_pat")
    m = mod.doi_pat.search("see doi:10.1000/xyz123 in text")
    assert m is not None and m.group(0).startswith("10.")  # encontrou e capturou

def test_imports_when_pyvis_absent(monkeypatch):
    """
    Simula ausência de 'pyvis' e verifica HAS_PYVIS=False.
    """
    _install_dummy_compute_ppx()
    _purge_module(MODULE_NAME)

    # Remover pyvis das sys.modules e bloquear import
    for k in list(sys.modules.keys()):
        if k.startswith("pyvis"):
            sys.modules.pop(k, None)

    import builtins
    real_import = builtins.__import__

    def fake_import(name, *a, **kw):
        if name.startswith("pyvis"):
            raise ModuleNotFoundError("pyvis not installed (simulado)")
        return real_import(name, *a, **kw)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    mod = importlib.import_module(MODULE_NAME)
    assert hasattr(mod, "HAS_PYVIS") and mod.HAS_PYVIS is False

def test_imports_when_louvain_absent(monkeypatch):
    """
    Simula ausência de 'community' (python-louvain) e verifica community_louvain=None.
    """
    _install_dummy_compute_ppx()
    _purge_module(MODULE_NAME)

    for k in list(sys.modules.keys()):
        if k == "community" or k.startswith("community."):
            sys.modules.pop(k, None)

    import builtins
    real_import = builtins.__import__

    def fake_import(name, *a, **kw):
        if name == "community":
            raise ModuleNotFoundError("community not installed (simulado)")
        return real_import(name, *a, **kw)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    mod = importlib.import_module(MODULE_NAME)
    assert getattr(mod, "community_louvain", None) is None

def test_imports_when_igraph_absent(monkeypatch):
    """
    Simula ausência de igraph/leidenalg e verifica ig=None e leidenalg=None.
    """
    _install_dummy_compute_ppx()
    _purge_module(MODULE_NAME)

    for k in list(sys.modules.keys()):
        if k in ("igraph", "leidenalg") or k.startswith("igraph.") or k.startswith("leidenalg."):
            sys.modules.pop(k, None)

    import builtins
    real_import = builtins.__import__

    def fake_import(name, *a, **kw):
        if name in ("igraph", "leidenalg"):
            raise ModuleNotFoundError(f"{name} not installed (simulado)")
        return real_import(name, *a, **kw)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    mod = importlib.import_module(MODULE_NAME)
    assert getattr(mod, "ig", None) is None
    assert getattr(mod, "leidenalg", None) is None

