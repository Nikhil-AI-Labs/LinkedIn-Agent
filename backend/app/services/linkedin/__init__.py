"""LinkedIn integration services."""

from app.services.linkedin.base import (
    LinkedInPost,
    LinkedInComment,
    LinkedInProfile,
    LinkedInResult,
    LinkedInClient,
    LinkedInPoster,
)
from app.services.linkedin.linkedin_manager import LinkedInManager

# Global instance
_linkedin_manager_instance: LinkedInManager | None = None


def get_linkedin_manager() -> LinkedInManager:
    """Get or create the global LinkedInManager instance.
    
    Returns:
        LinkedInManager singleton instance
    """
    global _linkedin_manager_instance
    
    if _linkedin_manager_instance is None:
        _linkedin_manager_instance = LinkedInManager()
    
    return _linkedin_manager_instance


__all__ = [
    "LinkedInPost",
    "LinkedInComment",
    "LinkedInProfile",
    "LinkedInResult",
    "LinkedInClient",
    "LinkedInPoster",
    "LinkedInManager",
    "get_linkedin_manager",
]
