from pydantic import BaseModel, Field


class DocumentedCode(BaseModel):
    """Represents a well documented source code content formatted as a plain ASCII string."""
    content: str = Field(..., description="The documented and updated python source code")


class UnittestCode(BaseModel):
    """Represents a unittest for the input source code content formatted as a plain ASCII string."""
    content: str = Field(..., description="The generated unittest code")
    imports: str = Field(..., description="The generated python module imports relative to project root directory")
