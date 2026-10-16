"""Explicit project-to-data binding shared by standalone advisory adapters."""
from pathlib import Path
import re

from .records import ToolkitError, confined

SESSION = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}')


def bound_workspace(project, relative='.'):
    """Resolve the install-time binding without accepting a retargeted alias."""
    project = Path(project).resolve(strict=True)
    workspace = project if relative == '.' else confined(project, relative)
    if workspace != project / relative or not workspace.is_dir():
        raise ToolkitError('hook workspace binding changed')
    return workspace


def in_scope(payload, workspace, project_root=None):
    """Accept only bound session cwd, excluding other nested workspaces."""
    if not isinstance(payload, dict):
        return False
    session, cwd = payload.get('session_id'), payload.get('cwd')
    if (not isinstance(session, str) or not SESSION.fullmatch(session)
            or not isinstance(cwd, str) or not Path(cwd).is_absolute()):
        return False
    try:
        workspace = Path(workspace).resolve(strict=True)
        project = Path(project_root or workspace).resolve(strict=True)
        if not workspace.is_relative_to(project):
            return False
        current = Path(cwd).resolve(strict=True)
        if not current.is_dir() or not current.is_relative_to(project):
            return False
        while True:
            if current != workspace and (current / 'cvtool.toml').exists():
                return False
            if current == project:
                break
            current = current.parent
        return True
    except (OSError, ValueError, RuntimeError):
        return False
