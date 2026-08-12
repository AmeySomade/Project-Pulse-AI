import asyncio
import os
import sys
from pathlib import Path

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools


# ---------------------------------------------------------
# Project paths
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"


# ---------------------------------------------------------
# MCP client configuration
# ---------------------------------------------------------

def create_mcp_client() -> MultiServerMCPClient:
    """
    Create an MCP client configured to launch the
    ProjectPulse MCP server as a local stdio subprocess.
    """

    env = os.environ.copy()

    existing_pythonpath = env.get("PYTHONPATH", "")

    if existing_pythonpath:
        env["PYTHONPATH"] = (
            f"{SRC_DIR}{os.pathsep}{existing_pythonpath}"
        )
    else:
        env["PYTHONPATH"] = str(SRC_DIR)

    return MultiServerMCPClient(
        {
            "projectpulse": {
                "transport": "stdio",
                "command": sys.executable,
                "args": [
                    "-m",
                    "projectpulse.mcp_server",
                ],
                "cwd": str(PROJECT_ROOT),
                "env": env,
            }
        }
    )


# ---------------------------------------------------------
# MCP verification
# ---------------------------------------------------------

async def main():
    client = create_mcp_client()

    print("=" * 60)
    print("PROJECTPULSE MCP CLIENT")
    print("=" * 60)

    async with client.session("projectpulse") as session:

        # Discover MCP tools and convert them into
        # LangChain-compatible tools.
        tools = await load_mcp_tools(session)

        print("\nDiscovered MCP tools:")

        for tool in tools:
            print(f"- {tool.name}")
            print(f"  Description: {tool.description}")

        tool_map = {
            tool.name: tool
            for tool in tools
        }

        expected_tools = {
            "search_project_history",
            "investigate_project",
        }

        discovered_tools = set(tool_map.keys())

        missing_tools = expected_tools - discovered_tools

        if missing_tools:
            raise RuntimeError(
                f"Missing expected MCP tools: {missing_tools}"
            )

        print("\nAll expected MCP tools discovered successfully.")

        # -------------------------------------------------
        # Test Tool 1
        # -------------------------------------------------

        print("\n" + "=" * 60)
        print("TEST 1: DIRECT PROJECT HISTORY SEARCH")
        print("=" * 60)

        search_result = await tool_map[
            "search_project_history"
        ].ainvoke(
            {
                "query": (
                    "What work was done on GitHub integration?"
                ),
                "top_k": 2,
            }
        )

        print("\nTool result:")
        print(search_result)

        # -------------------------------------------------
        # Test Tool 2
        # -------------------------------------------------

        print("\n" + "=" * 60)
        print("TEST 2: MULTI-STEP PROJECT INVESTIGATION")
        print("=" * 60)

        investigation_result = await tool_map[
            "investigate_project"
        ].ainvoke(
            {
                "query": (
                    "What changed in ProjectPulse and "
                    "what is the current project status?"
                ),
                "top_k_per_query": 2,
            }
        )

        print("\nTool result:")
        print(investigation_result)

        print("\n" + "=" * 60)
        print("MCP CLIENT VERIFICATION PASSED")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())