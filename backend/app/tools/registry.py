import inspect
import time
import logging
from typing import Any, Callable, Dict, Optional, Type
from pydantic import BaseModel, Field, create_model

logger = logging.getLogger(__name__)

class ToolMetadata(BaseModel):
    name: str
    description: str
    category: str
    parameters_schema: dict[str, Any]
    output_schema: dict[str, Any]

class ToolExecutionResult(BaseModel):
    tool_name: str
    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._metadata: Dict[str, ToolMetadata] = {}

    def register(
        self,
        name: str,
        description: str,
        category: str,
        param_model: Optional[Type[BaseModel]] = None,
        output_model: Optional[Type[BaseModel]] = None
    ):
        """Decorator to register a tool function into the registry."""
        def decorator(func: Callable):
            self._tools[name] = func

            # Derive parameters schema from pydantic model or doc/annotations
            if param_model:
                param_schema = param_model.model_json_schema()
            else:
                param_schema = {"type": "object", "properties": {}}

            if output_model:
                out_schema = output_model.model_json_schema()
            else:
                out_schema = {"type": "object", "properties": {}}

            self._metadata[name] = ToolMetadata(
                name=name,
                description=description,
                category=category,
                parameters_schema=param_schema,
                output_schema=out_schema
            )
            return func
        return decorator

    def get_tool(self, name: str) -> Optional[Callable]:
        return self._tools.get(name)

    def get_metadata(self, name: str) -> Optional[ToolMetadata]:
        return self._metadata.get(name)

    def list_tools(self) -> list[ToolMetadata]:
        return list(self._metadata.values())

    def execute(self, name: str, **kwargs) -> ToolExecutionResult:
        """Executes a registered tool with timing and unified error handling."""
        tool_fn = self._tools.get(name)
        if not tool_fn:
            return ToolExecutionResult(
                tool_name=name,
                success=False,
                error=f"Tool '{name}' is not registered in the system registry.",
                execution_time_ms=0.0
            )

        start_time = time.perf_counter()
        try:
            # Filter kwargs to only arguments accepted by tool_fn unless accepts **kwargs
            sig = inspect.signature(tool_fn)
            has_var_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
            if not has_var_kwargs:
                valid_kwargs = {k: v for k, v in kwargs.items() if k in sig.parameters}
            else:
                valid_kwargs = kwargs

            result = tool_fn(**valid_kwargs)
            duration_ms = (time.perf_counter() - start_time) * 1000.0

            return ToolExecutionResult(
                tool_name=name,
                success=True,
                data=result,
                execution_time_ms=round(duration_ms, 2)
            )
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error(f"Error executing tool '{name}': {str(e)}", exc_info=True)
            return ToolExecutionResult(
                tool_name=name,
                success=False,
                error=f"{type(e).__name__}: {str(e)}",
                execution_time_ms=round(duration_ms, 2)
            )

registry = ToolRegistry()
