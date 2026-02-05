"""Code Repository Processor - Extract knowledge from code repositories.

Parses source code, documentation, and commit history to build
understanding of coding style, projects, and technical expertise.
"""

from pathlib import Path
from typing import Optional, Iterator
from dataclasses import dataclass, field
import hashlib
import subprocess


@dataclass
class CodeFile:
    """A processed code file."""
    
    file_path: str
    language: str
    content: str
    line_count: int
    functions: list[str] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    docstrings: list[str] = field(default_factory=list)
    
    @property
    def id(self) -> str:
        """Generate unique ID for this file."""
        return hashlib.md5(self.file_path.encode()).hexdigest()
    
    def to_text(self) -> str:
        """Convert to text for embedding."""
        parts = [f"File: {self.file_path} ({self.language})"]
        
        if self.docstrings:
            parts.append("Documentation:")
            parts.extend(self.docstrings[:3])  # First 3 docstrings
        
        if self.functions:
            parts.append(f"Functions: {', '.join(self.functions[:10])}")
        
        if self.classes:
            parts.append(f"Classes: {', '.join(self.classes[:10])}")
        
        return "\n".join(parts)


@dataclass
class CommitInfo:
    """Information about a git commit."""
    
    hash: str
    message: str
    author: str
    date: str
    files_changed: list[str] = field(default_factory=list)
    
    def to_text(self) -> str:
        """Convert to text for embedding."""
        return f"Commit: {self.message} ({self.date})"


@dataclass
class ProcessedRepository:
    """A fully processed code repository."""
    
    name: str
    path: str
    files: list[CodeFile] = field(default_factory=list)
    commits: list[CommitInfo] = field(default_factory=list)
    readme: Optional[str] = None
    languages: dict[str, int] = field(default_factory=dict)
    
    @property
    def file_count(self) -> int:
        return len(self.files)
    
    @property
    def commit_count(self) -> int:
        return len(self.commits)


class CodeRepositoryProcessor:
    """Process code repositories for personal AI training.
    
    Extracts code structure, documentation, and commit history
    to understand coding patterns and project knowledge.
    
    Example:
        >>> processor = CodeRepositoryProcessor()
        >>> repo = processor.process_repository("path/to/repo")
        >>> for file in repo.files:
        ...     print(file.file_path, file.language)
    """
    
    # Language detection by extension
    LANGUAGE_MAP = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "javascript",
        ".tsx": "typescript",
        ".java": "java",
        ".go": "go",
        ".rs": "rust",
        ".cpp": "cpp",
        ".c": "c",
        ".h": "c",
        ".cs": "csharp",
        ".rb": "ruby",
        ".php": "php",
        ".swift": "swift",
        ".kt": "kotlin",
        ".md": "markdown",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".sql": "sql",
        ".sh": "shell",
        ".ps1": "powershell",
    }
    
    # Files/directories to skip
    SKIP_PATTERNS = {
        "node_modules", ".git", "__pycache__", ".venv", "venv",
        "dist", "build", ".next", "target", ".idea", ".vscode",
        "*.pyc", "*.pyo", "*.so", "*.dll", "*.exe",
    }
    
    def __init__(
        self,
        max_file_size: int = 100_000,  # 100KB
        include_commits: bool = True,
        max_commits: int = 100,
    ) -> None:
        """Initialize the repository processor.
        
        Args:
            max_file_size: Maximum file size to process in bytes.
            include_commits: Whether to parse git history.
            max_commits: Maximum commits to include.
        """
        self.max_file_size = max_file_size
        self.include_commits = include_commits
        self.max_commits = max_commits
    
    def process_repository(self, repo_path: str | Path) -> ProcessedRepository:
        """Process a code repository.
        
        Args:
            repo_path: Path to the repository.
        
        Returns:
            ProcessedRepository: Processed repository data.
        """
        path = Path(repo_path)
        
        if not path.is_dir():
            raise ValueError(f"Not a directory: {repo_path}")
        
        repo = ProcessedRepository(
            name=path.name,
            path=str(path),
        )
        
        # Process code files
        repo.files = list(self._process_files(path))
        
        # Count languages
        for file in repo.files:
            lang = file.language
            repo.languages[lang] = repo.languages.get(lang, 0) + 1
        
        # Read README if present
        for readme_name in ["README.md", "README.txt", "README"]:
            readme_path = path / readme_name
            if readme_path.exists():
                try:
                    repo.readme = readme_path.read_text(encoding="utf-8")[:5000]
                except Exception:
                    pass
                break
        
        # Get git history
        if self.include_commits and (path / ".git").exists():
            repo.commits = list(self._get_commits(path))
        
        return repo
    
    def _process_files(self, repo_path: Path) -> Iterator[CodeFile]:
        """Process all code files in a repository.
        
        Args:
            repo_path: Path to the repository.
        
        Yields:
            CodeFile: Processed code files.
        """
        for file_path in repo_path.rglob("*"):
            # Skip directories
            if file_path.is_dir():
                continue
            
            # Skip excluded patterns
            rel_path = file_path.relative_to(repo_path)
            if any(part in self.SKIP_PATTERNS for part in rel_path.parts):
                continue
            
            # Check file size
            try:
                if file_path.stat().st_size > self.max_file_size:
                    continue
            except OSError:
                continue
            
            # Determine language
            ext = file_path.suffix.lower()
            language = self.LANGUAGE_MAP.get(ext)
            if not language:
                continue
            
            try:
                content = file_path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            
            code_file = CodeFile(
                file_path=str(rel_path),
                language=language,
                content=content,
                line_count=content.count("\n") + 1,
            )
            
            # Extract code structure based on language
            if language == "python":
                self._parse_python(content, code_file)
            
            yield code_file
    
    def _parse_python(self, content: str, code_file: CodeFile) -> None:
        """Parse Python-specific structure.
        
        Args:
            content: File content.
            code_file: CodeFile to populate.
        """
        lines = content.split("\n")
        in_docstring = False
        docstring_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            # Detect docstrings
            if '"""' in stripped or "'''" in stripped:
                if in_docstring:
                    in_docstring = False
                    if docstring_lines:
                        code_file.docstrings.append(" ".join(docstring_lines))
                        docstring_lines = []
                else:
                    in_docstring = True
                continue
            
            if in_docstring:
                docstring_lines.append(stripped)
                continue
            
            # Detect imports
            if stripped.startswith("import ") or stripped.startswith("from "):
                code_file.imports.append(stripped)
            
            # Detect functions
            if stripped.startswith("def "):
                func_name = stripped[4:].split("(")[0]
                code_file.functions.append(func_name)
            
            # Detect classes
            if stripped.startswith("class "):
                class_name = stripped[6:].split("(")[0].split(":")[0]
                code_file.classes.append(class_name)
    
    def _get_commits(self, repo_path: Path) -> Iterator[CommitInfo]:
        """Get git commit history.
        
        Args:
            repo_path: Path to the repository.
        
        Yields:
            CommitInfo: Commit information.
        """
        try:
            result = subprocess.run(
                [
                    "git", "log",
                    f"-{self.max_commits}",
                    "--pretty=format:%H|%s|%an|%ad",
                    "--date=short"
                ],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            if result.returncode != 0:
                return
            
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                
                parts = line.split("|", 3)
                if len(parts) >= 4:
                    yield CommitInfo(
                        hash=parts[0][:8],
                        message=parts[1],
                        author=parts[2],
                        date=parts[3],
                    )
                    
        except (subprocess.SubprocessError, OSError):
            pass


def process_repository(path: str) -> ProcessedRepository:
    """Process a code repository.
    
    Args:
        path: Path to the repository.
    
    Returns:
        ProcessedRepository: Processed data.
    """
    processor = CodeRepositoryProcessor()
    return processor.process_repository(path)
