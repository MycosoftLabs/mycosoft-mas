import pytest
from unittest.mock import Mock, patch
from mycosoft_mas.dependencies.dependency_manager import DependencyManager

@pytest.fixture
def dependency_manager():
    return DependencyManager()

def test_dependency_manager_initialization(dependency_manager):
    assert dependency_manager.dependencies == {}
    assert dependency_manager.dependency_graph == {}
    assert dependency_manager.installed_versions == {}
    assert dependency_manager.update_history == []

def test_add_dependency(dependency_manager):
    dependency_manager.add_dependency("test_package", "1.0.0")
    assert "test_package" in dependency_manager.dependencies
    assert dependency_manager.dependencies["test_package"] == "1.0.0"

def test_remove_dependency(dependency_manager):
    dependency_manager.add_dependency("test_package", "1.0.0")
    dependency_manager.remove_dependency("test_package")
    assert "test_package" not in dependency_manager.dependencies

def test_add_dependency_relationship(dependency_manager):
    dependency_manager.add_dependency_relationship("test_package", "required_package")
    assert "test_package" in dependency_manager.dependency_graph
    assert "required_package" in dependency_manager.dependency_graph["test_package"]

def test_remove_dependency_relationship(dependency_manager):
    dependency_manager.add_dependency_relationship("test_package", "required_package")
    dependency_manager.remove_dependency_relationship("test_package", "required_package")
    assert "required_package" not in dependency_manager.dependency_graph["test_package"]

def test_check_dependencies(dependency_manager):
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.stdout = "Package Version\nnumpy 1.24.3\npandas 2.0.3"
        result = dependency_manager.check_dependencies()
        assert "numpy" in result
        assert "pandas" in result
        assert result["numpy"] == "1.24.3"
        assert result["pandas"] == "2.0.3"

def test_update_dependency(dependency_manager):
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        result = dependency_manager.update_dependency("test_package", "2.0.0")
        assert result["status"] == "success"
        mock_run.assert_called_with(
            ["poetry", "update", "test_package"],
            capture_output=True,
            text=True
        )

def test_install_dependency(dependency_manager):
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        result = dependency_manager.install_dependency("test_package", "1.0.0")
        assert result["status"] == "success"
        mock_run.assert_called_with(
            ["poetry", "add", "test_package==1.0.0"],
            capture_output=True,
            text=True
        )

def test_uninstall_dependency(dependency_manager):
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        result = dependency_manager.uninstall_dependency("test_package")
        assert result["status"] == "success"
        mock_run.assert_called_with(
            ["poetry", "remove", "test_package"],
            capture_output=True,
            text=True
        )

def test_resolve_dependencies(dependency_manager):
    dependency_manager.add_dependency("test_package", "1.0.0")
    dependency_manager.add_dependency_relationship("test_package", "required_package")
    resolved = dependency_manager.resolve_dependencies()
    assert "test_package" in resolved
    assert "required_package" in resolved

def test_check_for_updates(dependency_manager):
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.stdout = "Package Current Latest\nnumpy 1.24.3 1.25.0\npandas 2.0.3 2.1.0"
        updates = dependency_manager.check_for_updates()
        assert "numpy" in updates
        assert "pandas" in updates
        assert updates["numpy"]["current"] == "1.24.3"
        assert updates["numpy"]["latest"] == "1.25.0"

def test_update_all_dependencies(dependency_manager):
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        result = dependency_manager.update_all_dependencies()
        assert result["status"] == "success"
        mock_run.assert_called_with(
            ["poetry", "update"],
            capture_output=True,
            text=True
        )

def test_generate_dependency_report(dependency_manager):
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.stdout = "Package Version\nnumpy 1.24.3\npandas 2.0.3"
        report = dependency_manager.generate_dependency_report()
        assert "installed_dependencies" in report
        assert "dependency_graph" in report
        assert "update_history" in report
        assert "numpy" in report["installed_dependencies"]
        assert "pandas" in report["installed_dependencies"] 