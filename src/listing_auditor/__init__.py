"""listing-auditor: a rules + statistics engine that scores rental listings and proposes safe fixes."""
from .config import load_config
from .engine import audit
from .models import AuditResult, Finding, Listing, Patch, Severity

__all__ = ["audit", "load_config", "AuditResult", "Finding", "Listing", "Patch", "Severity"]
__version__ = "0.1.0"
