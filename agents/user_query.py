"""
User Query Component - Simple input handler for user queries
"""
from typing import Optional
from pydantic import BaseModel


class UserQuery(BaseModel):
    """User Query data model"""
    query: str
    timezone: Optional[str] = None
    
    def __str__(self) -> str:
        return f"UserQuery(query='{self.query}', timezone='{self.timezone}')"


class UserQueryHandler:
    """Simple handler for user queries"""
    
    def __init__(self, default_timezone: str = "UTC"):
        self.default_timezone = default_timezone
    
    def process_query(self, query: str, timezone: Optional[str] = None) -> UserQuery:
        """
        Process a user query and return a UserQuery object
        
        Args:
            query: The raw user query string
            timezone: Optional timezone (defaults to instance default)
            
        Returns:
            UserQuery object
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        return UserQuery(
            query=query.strip(),
            timezone=timezone or self.default_timezone
        )
    
    def validate_query(self, query: str) -> bool:
        """
        Validate if the query is acceptable
        
        Args:
            query: The query string to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not query or not query.strip():
            return False
        
        # Basic validation - query should have some content
        return len(query.strip()) > 0


# Example usage
if __name__ == "__main__":
    handler = UserQueryHandler(default_timezone="America/New_York")
    
    # Test basic functionality
    test_queries = [
        "Complete Math HW by 14 Nov",
        "Call Mom tomorrow for 30 minutes", 
        "Plan John's Bday by 21st November",
        "Work on project from 9am to 5pm",
        "Study for 2 hours tonight"
    ]
    
    print("Testing User Query Handler:")
    for query in test_queries:
        try:
            uq = handler.process_query(query)
            print(f"✅ '{query}' -> {uq}")
        except Exception as e:
            print(f"❌ '{query}' -> Error: {e}")
