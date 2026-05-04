"""Fail if MCP schema descriptions become too large.

MCP clients usually receive tool and prompt metadata before choosing a call.
Keeping descriptions concise makes the server cheaper and less distracting.
"""

import anyio

from qe_mcp.server import mcp


TOOL_DESCRIPTION_BUDGET = 8_000
PROMPT_DESCRIPTION_BUDGET = 5_000
MAX_SINGLE_TOOL_DESCRIPTION = 600


async def main() -> None:
    tools = await mcp.list_tools()
    prompts = await mcp.list_prompts()

    tool_total = sum(len(tool.description or "") for tool in tools)
    prompt_total = sum(len(prompt.description or "") for prompt in prompts)
    oversized = [
        (tool.name, len(tool.description or ""))
        for tool in tools
        if len(tool.description or "") > MAX_SINGLE_TOOL_DESCRIPTION
    ]

    print(f"tools={len(tools)} tool_description_chars={tool_total}")
    print(f"prompts={len(prompts)} prompt_description_chars={prompt_total}")

    errors: list[str] = []
    if tool_total > TOOL_DESCRIPTION_BUDGET:
        errors.append(
            f"tool descriptions use {tool_total} chars; budget is {TOOL_DESCRIPTION_BUDGET}"
        )
    if prompt_total > PROMPT_DESCRIPTION_BUDGET:
        errors.append(
            f"prompt descriptions use {prompt_total} chars; budget is {PROMPT_DESCRIPTION_BUDGET}"
        )
    if oversized:
        details = ", ".join(f"{name}={size}" for name, size in oversized)
        errors.append(
            "tool descriptions exceed single-tool budget "
            f"{MAX_SINGLE_TOOL_DESCRIPTION}: {details}"
        )

    if errors:
        raise SystemExit("\n".join(errors))

    print("MCP schema budget ok")


if __name__ == "__main__":
    anyio.run(main)
