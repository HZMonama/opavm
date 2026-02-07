from __future__ import annotations

from dataclasses import dataclass

from opavm.errors import OpavmError


@dataclass(frozen=True)
class ToolSpec:
    name: str
    display_name: str
    binary_base: str
    default_repo: str
    repo_env_var: str


SUPPORTED_TOOLS: dict[str, ToolSpec] = {
    "opa": ToolSpec(
        name="opa",
        display_name="OPA",
        binary_base="opa",
        default_repo="open-policy-agent/opa",
        repo_env_var="OPAVM_GITHUB_REPO",
    ),
    "regal": ToolSpec(
        name="regal",
        display_name="Regal",
        binary_base="regal",
        default_repo="StyraInc/regal",
        repo_env_var="OPAVM_REGAL_GITHUB_REPO",
    ),
}


def get_tool(tool: str) -> ToolSpec:
    normalized = tool.lower().strip()
    spec = SUPPORTED_TOOLS.get(normalized)
    if spec is None:
        options = ", ".join(sorted(SUPPORTED_TOOLS))
        raise OpavmError("Unknown tool.", f"Supported tools: {options}")
    return spec
