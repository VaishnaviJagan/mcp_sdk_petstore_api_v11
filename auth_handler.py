"""Authentication handler for API calls."""
from typing import Dict, Optional
import base64
import logging

logger = logging.getLogger(__name__)


class AuthHandler:
    """Handles authentication for API calls."""
    
    def __init__(self, auth_config: Optional[Dict]):
        """
        Initialize with authentication configuration.
        
        Args:
            auth_config: Dict with keys:
                - type: "apiKey" | "http" | "oauth2"
                - credentials: Dict with auth-specific fields
        """
        self.auth_config = auth_config or {}
        self.auth_type = self.auth_config.get("type")
        self.credentials = self.auth_config.get("credentials", {})
        
        logger.debug(f"Initialized AuthHandler with type: {self.auth_type}")
    
    def get_headers(self) -> Dict[str, str]:
        """
        Get authentication headers to add to requests.
        
        Returns:
            Dict of headers to include
        """
        if not self.auth_type:
            return {}
        
        if self.auth_type == "apiKey":
            return self._handle_api_key_header()
        
        elif self.auth_type == "http":
            return self._handle_http_auth()
        
        elif self.auth_type == "oauth2":
            return self._handle_oauth2()
        
        logger.warning(f"Unknown auth type: {self.auth_type}")
        return {}
    
    def get_query_params(self) -> Dict[str, str]:
        """
        Get authentication query parameters.
        
        Needed for API keys in query string.
        
        Returns:
            Dict of query params to include
        """
        if self.auth_type == "apiKey" and self.credentials.get("location") == "query":
            name = self.credentials.get("name", "api_key")
            value = self.credentials.get("value", "")
            return {name: value}
        
        return {}
    
    def _handle_api_key_header(self) -> Dict[str, str]:
        """
        Handle API key authentication in header.
        
        Returns:
            Dict with API key header
        """
        location = self.credentials.get("location", "header")
        
        if location == "header":
            name = self.credentials.get("name", "X-API-Key")
            value = self.credentials.get("value", "")
            
            logger.debug(f"Using API key in header: {name}")
            return {name: value}
        
        # Query params handled separately
        return {}
    
    def _handle_http_auth(self) -> Dict[str, str]:
        """
        Handle HTTP authentication (Basic, Bearer).
        
        Returns:
            Dict with Authorization header
        """
        scheme = self.credentials.get("scheme", "bearer").lower()
        
        if scheme == "bearer":
            token = self.credentials.get("token", "")
            logger.debug("Using Bearer authentication")
            return {"Authorization": f"Bearer {token}"}
        
        elif scheme == "basic":
            username = self.credentials.get("username", "")
            password = self.credentials.get("password", "")
            
            # Encode credentials
            credentials_str = f"{username}:{password}"
            credentials_bytes = credentials_str.encode('utf-8')
            encoded = base64.b64encode(credentials_bytes).decode('utf-8')
            
            logger.debug("Using Basic authentication")
            return {"Authorization": f"Basic {encoded}"}
        
        logger.warning(f"Unknown HTTP scheme: {scheme}")
        return {}
    
    def _handle_oauth2(self) -> Dict[str, str]:
        """
        Handle OAuth2 authentication.
        
        For now, assumes access_token is provided.
        TODO: Implement token refresh flow.
        
        Returns:
            Dict with Authorization header
        """
        access_token = self.credentials.get("access_token", "")
        
        if access_token:
            logger.debug("Using OAuth2 authentication")
            return {"Authorization": f"Bearer {access_token}"}
        
        logger.warning("OAuth2 access_token not provided")
        return {}
    
    def is_configured(self) -> bool:
        """
        Check if authentication is configured.
        
        Returns:
            True if auth is configured
        """
        return bool(self.auth_type and self.credentials)
