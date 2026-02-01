#!/usr/bin/env python3
"""
Verification script for MedWriter Phase One installation.
Tests all components without requiring real API keys.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")

    try:
        from src.config.settings import Settings
        from src.mcp_server.server import mcp, _web_search_impl, _medical_knowledge_impl, _citation_generator_impl
        from src.worker.mcp_client import MCPClient
        from src.worker.agent import MedicalArticleAgent
        from src.worker.worker import Worker
        print("✓ All imports successful")
        return True
    except Exception as e:
        print(f"✗ Import error: {e}")
        return False


def test_configuration():
    """Test configuration system."""
    print("\nTesting configuration...")

    try:
        from src.config.settings import Settings

        # Test with minimal config
        settings = Settings(
            llm_provider="openai",
            openai_api_key="test-key",
            model_name="gpt-3.5-turbo",
        )

        assert settings.llm_provider == "openai"
        assert settings.model_name == "gpt-3.5-turbo"

        print("✓ Configuration system working")
        return True
    except Exception as e:
        print(f"✗ Configuration error: {e}")
        return False


def test_mcp_server_tools():
    """Test MCP server tools."""
    print("\nTesting MCP server tools...")

    try:
        from src.mcp_server.server import _web_search_impl, _medical_knowledge_impl, _citation_generator_impl

        # Test web_search
        result = _web_search_impl("diabetes")
        assert "query" in result
        assert len(result["results"]) > 0
        print(f"  ✓ web_search returned {len(result['results'])} results")

        # Test medical_knowledge
        result = _medical_knowledge_impl("hypertension")
        assert "topic" in result
        assert "definition" in result
        print(f"  ✓ medical_knowledge returned data for {result['topic']}")

        # Test citation_generator
        result = _citation_generator_impl("heart disease", 3)
        assert "citations" in result
        assert len(result["citations"]) == 3
        print(f"  ✓ citation_generator returned {len(result['citations'])} citations")

        print("✓ All MCP server tools working")
        return True
    except Exception as e:
        print(f"✗ MCP server tools error: {e}")
        return False


def test_mcp_server_registration():
    """Test that tools are registered with FastMCP."""
    print("\nTesting MCP server tool registration...")

    try:
        import asyncio
        from src.mcp_server.server import mcp

        async def check_tools():
            tools = await mcp.get_tools()
            return tools

        tools = asyncio.run(check_tools())
        # Tools is a dictionary
        if isinstance(tools, dict):
            tool_names = list(tools.keys())
        else:
            tool_names = [t.name if hasattr(t, 'name') else str(t) for t in tools]

        assert "web_search" in tool_names
        assert "medical_knowledge" in tool_names
        assert "citation_generator" in tool_names

        print(f"  ✓ Found {len(tool_names)} registered tools: {tool_names}")
        print("✓ MCP server tool registration working")
        return True
    except Exception as e:
        print(f"✗ MCP server registration error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_project_structure():
    """Test project structure."""
    print("\nTesting project structure...")

    required_dirs = [
        "src/config",
        "src/mcp_server",
        "src/worker",
        "src/cli",
        "tests",
    ]

    required_files = [
        "src/config/settings.py",
        "src/mcp_server/server.py",
        "src/worker/mcp_client.py",
        "src/worker/agent.py",
        "src/worker/worker.py",
        "src/cli/main.py",
        "pyproject.toml",
        "README.md",
        ".env.example",
    ]

    missing_dirs = []
    for dir_path in required_dirs:
        if not (project_root / dir_path).is_dir():
            missing_dirs.append(dir_path)

    missing_files = []
    for file_path in required_files:
        if not (project_root / file_path).is_file():
            missing_files.append(file_path)

    if missing_dirs or missing_files:
        if missing_dirs:
            print(f"✗ Missing directories: {missing_dirs}")
        if missing_files:
            print(f"✗ Missing files: {missing_files}")
        return False

    print(f"  ✓ All {len(required_dirs)} required directories present")
    print(f"  ✓ All {len(required_files)} required files present")
    print("✓ Project structure correct")
    return True


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("MedWriter Phase One - Installation Verification")
    print("=" * 60)

    tests = [
        ("Project Structure", test_project_structure),
        ("Imports", test_imports),
        ("Configuration", test_configuration),
        ("MCP Server Tools", test_mcp_server_tools),
        ("MCP Server Registration", test_mcp_server_registration),
    ]

    results = []
    for name, test_func in tests:
        try:
            results.append(test_func())
        except Exception as e:
            print(f"\n✗ {name} test failed with exception: {e}")
            results.append(False)

    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    for (name, _), result in zip(tests, results):
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} - {name}")

    print("\n" + "-" * 60)
    print(f"Total: {passed}/{total} tests passed")
    print("=" * 60)

    if passed == total:
        print("\n🎉 All verification tests passed!")
        print("\nNext steps:")
        print("1. Set your API keys in .env file")
        print("2. Run the tests: pytest")
        print("3. Start the CLI: python -m src.cli.main")
        return 0
    else:
        print("\n⚠️  Some verification tests failed.")
        print("Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
