"""Cowork OS Tools - Native file system and terminal access."""

import asyncio
from pathlib import Path
from ..registry import get_tool_registry

registry = get_tool_registry()

@registry.tool(
    name="read_file",
    description="Read the contents of a file.",
)
async def read_file(path: str) -> str:
    """Read a file."""
    try:
        file_path = Path(path).resolve()
        return file_path.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading file '{path}': {e}"

@registry.tool(
    name="write_file",
    description="Write content to a file, overwriting existing content.",
)
async def write_file(path: str, content: str) -> str:
    """Write to a file."""
    try:
        file_path = Path(path).resolve()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Error writing to file '{path}': {e}"

@registry.tool(
    name="list_directory",
    description="List the contents of a directory.",
)
async def list_directory(path: str) -> str:
    """List directory contents."""
    try:
        file_path = Path(path).resolve()
        if not file_path.exists() or not file_path.is_dir():
            return f"Error: '{path}' is not a valid directory."
        
        entries = []
        for entry in file_path.iterdir():
            if entry.is_dir():
                entries.append(f"{entry.name}/")
            else:
                entries.append(entry.name)
        return "\n".join(sorted(entries))
    except Exception as e:
        return f"Error listing directory '{path}': {e}"

@registry.tool(
    name="run_command",
    description="Run a shell command and return its output. Use carefully as this executes on the host system.",
)
async def run_command(command: str) -> str:
    """Run a shell command."""
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        
        result = []
        if stdout:
            result.append(stdout.decode('utf-8'))
        if stderr:
            result.append(f"STDERR:\n{stderr.decode('utf-8')}")
            
        if not result:
            return "Command executed successfully with no output."
            
        return "\n".join(result)
    except Exception as e:
        return f"Error executing command '{command}': {e}"
