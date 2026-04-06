from mycosoft_mas.llm.backend_selection import MYCA_CORE, get_backend_for_role


def _clear_mode_env(monkeypatch):
    for key in (
        "MYCA_BACKEND_MODE",
        "MYCA_BACKEND_MODE_CORPORATE",
        "MYCA_BACKEND_MODE_INFRA",
        "MYCA_BACKEND_MODE_DEVICE",
        "MYCA_BACKEND_MODE_ROUTE",
        "MYCA_BACKEND_MODE_NLM",
        "MYCA_BACKEND_MODE_CONSCIOUSNESS",
        "NEMOTRON_BASE_URL",
        "NEMOTRON_MODEL_SUPER",
        "NEMOTRON_MODEL_CORPORATE",
        "OLLAMA_BASE_URL",
        "OLLAMA_MODEL",
    ):
        monkeypatch.delenv(key, raising=False)


def test_default_hybrid_uses_existing_resolution(monkeypatch):
    _clear_mode_env(monkeypatch)
    selection = get_backend_for_role(MYCA_CORE)
    assert selection.provider in {"nemotron", "ollama"}
    assert selection.model


def test_global_llama_mode_forces_ollama(monkeypatch):
    _clear_mode_env(monkeypatch)
    monkeypatch.setenv("MYCA_BACKEND_MODE", "llama")
    monkeypatch.setenv("NEMOTRON_BASE_URL", "https://nemotron.example.com")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2")
    selection = get_backend_for_role(MYCA_CORE)
    assert selection.provider == "ollama"
    assert selection.model == "llama3.2"


def test_global_nemotron_mode_forces_nemotron(monkeypatch):
    _clear_mode_env(monkeypatch)
    monkeypatch.setenv("MYCA_BACKEND_MODE", "nemotron")
    monkeypatch.setenv("NEMOTRON_BASE_URL", "https://nemotron.example.com")
    monkeypatch.setenv("NEMOTRON_MODEL_CORPORATE", "nemotron-super-prod")
    selection = get_backend_for_role(MYCA_CORE)
    assert selection.provider == "nemotron"
    assert selection.base_url == "https://nemotron.example.com"
    assert selection.model == "nemotron-super-prod"


def test_category_override_wins_over_global(monkeypatch):
    _clear_mode_env(monkeypatch)
    monkeypatch.setenv("MYCA_BACKEND_MODE", "llama")
    monkeypatch.setenv("MYCA_BACKEND_MODE_CORPORATE", "nemotron")
    monkeypatch.setenv("NEMOTRON_BASE_URL", "https://nemotron.example.com")
    monkeypatch.setenv("NEMOTRON_MODEL_CORPORATE", "nemotron-super-cat")
    selection = get_backend_for_role(MYCA_CORE)
    assert selection.provider == "nemotron"
    assert selection.model == "nemotron-super-cat"


def test_nemotron_mode_without_base_url_falls_back_to_ollama(monkeypatch):
    _clear_mode_env(monkeypatch)
    monkeypatch.setenv("MYCA_BACKEND_MODE", "nemotron")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2")
    selection = get_backend_for_role(MYCA_CORE)
    assert selection.provider == "ollama"
    assert selection.base_url == "http://localhost:11434"
    assert selection.model == "llama3.2"

