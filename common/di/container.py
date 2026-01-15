"""
Dependency Injection Container.

This module provides a simple DI container for managing dependencies
and enabling better testability through dependency injection.
"""

from typing import Any, Dict, Callable, Optional, TypeVar, Type
from common.logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class DIContainer:
    """
    Simple Dependency Injection Container.
    
    This container manages object instances and factories, providing
    dependency injection capabilities for better testability.
    """
    
    def __init__(self):
        """Initialize the DI container."""
        self._instances: Dict[str, Any] = {}
        self._factories: Dict[str, Callable[[], Any]] = {}
        self._singletons: Dict[str, bool] = {}
        logger.debug("DIContainer initialized")
    
    def register(self, 
                name: str, 
                factory: Callable[[], Any],
                singleton: bool = True) -> None:
        """
        Register a factory function for creating an instance.
        
        Args:
            name: Unique identifier for the dependency
            factory: Factory function that creates the instance
            singleton: If True, factory is called once and result is cached.
                      If False, factory is called each time.
        """
        self._factories[name] = factory
        self._singletons[name] = singleton
        logger.debug("Registered dependency", name=name, singleton=singleton)
    
    def register_instance(self, name: str, instance: Any) -> None:
        """
        Register an existing instance.
        
        Args:
            name: Unique identifier for the dependency
            instance: Instance to register
        """
        self._instances[name] = instance
        logger.debug("Registered instance", name=name, instance_type=type(instance).__name__)
    
    def get(self, name: str) -> Any:
        """
        Get a dependency instance by name.
        
        Args:
            name: Unique identifier for the dependency
            
        Returns:
            Dependency instance
            
        Raises:
            ValueError: If dependency is not registered
        """
        # Check if instance already exists
        if name in self._instances:
            logger.debug("Returning cached instance", name=name)
            return self._instances[name]
        
        # Check if factory exists
        if name not in self._factories:
            logger.error("Dependency not found", name=name)
            raise ValueError(f"Dependency '{name}' is not registered")
        
        # Create instance using factory
        logger.debug("Creating instance", name=name, singleton=self._singletons.get(name, True))
        instance = self._factories[name]()
        
        # Cache if singleton
        if self._singletons.get(name, True):
            self._instances[name] = instance
            logger.debug("Cached singleton instance", name=name)
        
        return instance
    
    def has(self, name: str) -> bool:
        """
        Check if a dependency is registered.
        
        Args:
            name: Unique identifier for the dependency
            
        Returns:
            True if dependency is registered, False otherwise
        """
        return name in self._instances or name in self._factories
    
    def clear(self) -> None:
        """Clear all registered dependencies and instances."""
        self._instances.clear()
        self._factories.clear()
        self._singletons.clear()
        logger.debug("Container cleared")
    
    def reset_instance(self, name: str) -> None:
        """
        Reset a singleton instance, forcing it to be recreated.
        
        Args:
            name: Unique identifier for the dependency
        """
        if name in self._instances:
            del self._instances[name]
            logger.debug("Reset instance", name=name)


# Global container instance
_container: Optional[DIContainer] = None


def get_container() -> DIContainer:
    """
    Get the global DI container instance.
    
    Returns:
        DIContainer instance
    """
    global _container
    if _container is None:
        _container = DIContainer()
        logger.debug("Created global DI container")
    return _container


def set_container(container: DIContainer) -> None:
    """
    Set the global DI container instance (useful for testing).
    
    Args:
        container: DIContainer instance to set
    """
    global _container
    _container = container
    logger.debug("Set global DI container", 
                container_type=type(container).__name__)

