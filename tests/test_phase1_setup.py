"""Phase 1 基础设施测试

测试项目结构、配置文件和基础模块是否正确创建
"""

from pathlib import Path

import pytest


class TestProjectStructure:
    """测试项目结构"""

    @pytest.fixture
    def project_root(self) -> Path:
        """获取项目根目录"""
        return Path(__file__).parent.parent

    def test_src_structure(self, project_root: Path) -> None:
        """测试 src 目录结构"""
        src_dir = project_root / "src" / "lark_service"
        assert src_dir.exists(), "src/lark_service 目录应该存在"
        assert (src_dir / "__init__.py").exists(), "__init__.py 应该存在"

        # 检查核心模块
        assert (src_dir / "core").exists(), "core 模块应该存在"
        assert (src_dir / "core" / "__init__.py").exists()
        assert (src_dir / "core" / "models").exists(), "models 子模块应该存在"
        assert (src_dir / "core" / "storage").exists(), "storage 子模块应该存在"

        # 检查业务模块
        assert (src_dir / "messaging").exists(), "messaging 模块应该存在"
        assert (src_dir / "clouddoc").exists(), "clouddoc 模块应该存在"
        assert (src_dir / "contact").exists(), "contact 模块应该存在"
        assert (src_dir / "apaas").exists(), "apaas 模块应该存在"

        # 检查工具模块
        assert (src_dir / "utils").exists(), "utils 模块应该存在"
        assert (src_dir / "cli").exists(), "cli 模块应该存在"
        assert (src_dir / "db").exists(), "db 模块应该存在"

    def test_config_files(self, project_root: Path) -> None:
        """测试配置文件"""
        assert (project_root / "pyproject.toml").exists(), "pyproject.toml 应该存在"
        assert (project_root / "requirements.txt").exists(), "requirements.txt 应该存在"
        assert (project_root / ".gitignore").exists(), ".gitignore 应该存在"

    def test_docker_files(self, project_root: Path) -> None:
        """测试 Docker 相关文件"""
        assert (project_root / "Dockerfile").exists(), "Dockerfile 应该存在"
        assert (project_root / "docker-compose.yml").exists(), "docker-compose.yml 应该存在"

    def test_migration_files(self, project_root: Path) -> None:
        """测试数据库迁移文件"""
        assert (project_root / "alembic.ini").exists(), "alembic.ini 应该存在"
        migrations_dir = project_root / "migrations"
        assert migrations_dir.exists(), "migrations 目录应该存在"
        assert (migrations_dir / "env.py").exists(), "env.py 应该存在"
        assert (migrations_dir / "script.py.mako").exists(), "script.py.mako 应该存在"
        assert (migrations_dir / "init.sql").exists(), "init.sql 应该存在"

    def test_documentation(self, project_root: Path) -> None:
        """测试文档文件"""
        assert (project_root / "README.md").exists(), "README.md 应该存在"
        docs_dir = project_root / "docs"
        assert docs_dir.exists(), "docs 目录应该存在"
        assert (docs_dir / "architecture.md").exists(), "architecture.md 应该存在"
        assert (docs_dir / "deployment.md").exists(), "deployment.md 应该存在"
        assert (
            docs_dir / "development-environment.md"
        ).exists(), "development-environment.md 应该存在"


class TestPyprojectConfig:
    """测试 pyproject.toml 配置"""

    @pytest.fixture
    def project_root(self) -> Path:
        """获取项目根目录"""
        return Path(__file__).parent.parent

    def test_pyproject_exists(self, project_root: Path) -> None:
        """测试 pyproject.toml 存在"""
        pyproject_path = project_root / "pyproject.toml"
        assert pyproject_path.exists()

        content = pyproject_path.read_text()
        assert "lark-service" in content, "项目名称应该是 lark-service"
        assert "python" in content.lower(), "应该指定 Python 版本"

    def test_ruff_config(self, project_root: Path) -> None:
        """测试 Ruff 配置"""
        pyproject_path = project_root / "pyproject.toml"
        content = pyproject_path.read_text()
        assert "[tool.ruff]" in content, "应该有 Ruff 配置"

    def test_mypy_config(self, project_root: Path) -> None:
        """测试 Mypy 配置"""
        pyproject_path = project_root / "pyproject.toml"
        content = pyproject_path.read_text()
        assert "[tool.mypy]" in content, "应该有 Mypy 配置"

    def test_pytest_config(self, project_root: Path) -> None:
        """测试 Pytest 配置"""
        pyproject_path = project_root / "pyproject.toml"
        content = pyproject_path.read_text()
        assert "[tool.pytest.ini_options]" in content, "应该有 Pytest 配置"


class TestRequirements:
    """测试依赖文件"""

    @pytest.fixture
    def project_root(self) -> Path:
        """获取项目根目录"""
        return Path(__file__).parent.parent

    def test_requirements_exists(self, project_root: Path) -> None:
        """测试 requirements.txt 存在"""
        requirements_path = project_root / "requirements.txt"
        assert requirements_path.exists()

        content = requirements_path.read_text()
        # 检查核心依赖
        assert "lark-oapi" in content, "应该包含 lark-oapi"
        assert "pydantic" in content, "应该包含 pydantic"
        assert "SQLAlchemy" in content, "应该包含 SQLAlchemy"
        assert "psycopg2-binary" in content, "应该包含 psycopg2-binary"
        assert "pika" in content, "应该包含 pika"
        assert "cryptography" in content, "应该包含 cryptography"
        assert "alembic" in content, "应该包含 alembic"
        assert "click" in content, "应该包含 click"
        assert "rich" in content, "应该包含 rich"


class TestEnvironmentVariables:
    """测试环境变量"""

    def test_env_example_exists(self) -> None:
        """测试 .env.example 存在"""
        project_root = Path(__file__).parent.parent
        env_example = project_root / ".env.example"
        # .env.example 应该存在(如果有的话)
        # 这个测试是可选的,因为 Phase 1 可能还没创建
        if env_example.exists():
            content = env_example.read_text()
            assert "POSTGRES" in content, "应该包含 PostgreSQL 配置"


class TestImports:
    """测试模块导入"""

    def test_import_lark_service(self) -> None:
        """测试导入 lark_service 包"""
        try:
            import lark_service  # noqa: F401

            assert True, "应该能够导入 lark_service"
        except ImportError as e:
            pytest.fail(f"无法导入 lark_service: {e}")

    def test_import_core_modules(self) -> None:
        """测试导入核心模块"""
        try:
            from lark_service import core  # noqa: F401

            assert True, "应该能够导入 core 模块"
        except ImportError as e:
            pytest.fail(f"无法导入 core 模块: {e}")

    def test_import_business_modules(self) -> None:
        """测试导入业务模块"""
        try:
            from lark_service import (
                apaas,  # noqa: F401
                clouddoc,  # noqa: F401
                contact,  # noqa: F401
                messaging,  # noqa: F401
            )

            assert True, "应该能够导入所有业务模块"
        except ImportError as e:
            pytest.fail(f"无法导入业务模块: {e}")

    def test_import_utils(self) -> None:
        """测试导入工具模块"""
        try:
            from lark_service import (
                cli,  # noqa: F401
                db,  # noqa: F401
                utils,  # noqa: F401
            )

            assert True, "应该能够导入工具模块"
        except ImportError as e:
            pytest.fail(f"无法导入工具模块: {e}")
