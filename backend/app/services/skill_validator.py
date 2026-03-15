import io
import os
import zipfile
import re
from typing import Tuple, List

from app.core.config import settings

ALLOWED_EXTENSIONS = {".md", ".txt", ".py", ".json", ".yaml", ".yml", ".js"}
DANGEROUS_PATTERNS = [
    r"import\s+subprocess",
    r"import\s+os",
    r"__import__",
    r"exec\s*\(",
    r"eval\s*\(",
    r"open\s*\(",
    r"socket\.",
    r"urllib",
    r"requests\.",
]

REQUIRED_FRONTMATTER_FIELDS = ["name", "description", "version"]


def validate_skill_zip(zip_bytes: bytes, zip_size_mb: float) -> Tuple[bool, List[str]]:
    """
    Validate an uploaded skill ZIP file.
    Returns (is_valid, errors).
    """
    errors = []

    # 1. Size check
    if zip_size_mb > settings.max_skill_zip_mb:
        return False, [f"ZIP exceeds maximum size of {settings.max_skill_zip_mb}MB"]

    # 2. Is valid ZIP
    if not zipfile.is_zipfile(io.BytesIO(zip_bytes)):
        return False, ["File is not a valid ZIP archive"]

    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile as e:
        return False, [f"Bad ZIP file: {e}"]

    names = zf.namelist()

    # 3. Zip-slip check (path traversal)
    for name in names:
        if ".." in name or name.startswith("/") or name.startswith("\\"):
            errors.append(f"Path traversal detected in: {name}")

    # 4. Check SKILL.md exists at top level
    top_level_names = [n for n in names if "/" not in n.rstrip("/")]
    skill_md_candidates = [n for n in names if n == "SKILL.md" or n.endswith("/SKILL.md")]

    if "SKILL.md" not in names and not any(n == "SKILL.md" for n in top_level_names):
        # Try in any subdirectory if single folder zip
        skill_md_candidates = [n for n in names if os.path.basename(n) == "SKILL.md"]
        if not skill_md_candidates:
            errors.append("SKILL.md not found at top level of ZIP")

    # 5. Validate file extensions
    for name in names:
        if name.endswith("/"):
            continue  # directory entry
        ext = os.path.splitext(name)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            errors.append(f"Disallowed file extension: {name} ({ext})")

    # 6. Check SKILL.md frontmatter
    skill_md_path = None
    if "SKILL.md" in names:
        skill_md_path = "SKILL.md"
    elif skill_md_candidates:
        skill_md_path = skill_md_candidates[0]

    if skill_md_path:
        try:
            skill_md_content = zf.read(skill_md_path).decode("utf-8")
            fm_errors = validate_frontmatter(skill_md_content)
            errors.extend(fm_errors)
        except Exception as e:
            errors.append(f"Could not read SKILL.md: {e}")

    # 7. Check Python files for dangerous patterns
    for name in names:
        if name.endswith(".py") or name.endswith(".js"):
            try:
                content = zf.read(name).decode("utf-8", errors="replace")
                for pattern in DANGEROUS_PATTERNS:
                    if re.search(pattern, content):
                        errors.append(f"Potentially unsafe code in {name}: matches pattern '{pattern}'")
                        break
            except Exception:
                pass

    zf.close()

    is_valid = len(errors) == 0
    return is_valid, errors


def validate_frontmatter(content: str) -> List[str]:
    """Validate YAML frontmatter in SKILL.md."""
    errors = []

    if not content.startswith("---"):
        errors.append("SKILL.md must start with YAML frontmatter (---)")
        return errors

    parts = content.split("---", 2)
    if len(parts) < 3:
        errors.append("SKILL.md frontmatter not properly closed with ---")
        return errors

    frontmatter_text = parts[1]

    try:
        import yaml
        frontmatter = yaml.safe_load(frontmatter_text)
        if not isinstance(frontmatter, dict):
            errors.append("SKILL.md frontmatter must be a YAML mapping")
            return errors

        for field in REQUIRED_FRONTMATTER_FIELDS:
            if field not in frontmatter or not frontmatter[field]:
                errors.append(f"Missing required frontmatter field: {field}")

    except Exception as e:
        errors.append(f"Invalid YAML frontmatter: {e}")

    return errors


def parse_skill_metadata(zip_bytes: bytes) -> dict:
    """Parse metadata from SKILL.md frontmatter."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
        skill_md_path = None
        for name in zf.namelist():
            if os.path.basename(name) == "SKILL.md":
                skill_md_path = name
                break

        if not skill_md_path:
            return {}

        content = zf.read(skill_md_path).decode("utf-8")
        zf.close()

        if not content.startswith("---"):
            return {}

        parts = content.split("---", 2)
        if len(parts) < 3:
            return {}

        import yaml
        frontmatter = yaml.safe_load(parts[1])
        return frontmatter if isinstance(frontmatter, dict) else {}
    except Exception:
        return {}
