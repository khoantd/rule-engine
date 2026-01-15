"""
Factory Pattern Implementation.

This module provides factory classes for creating rule engine components
with dependency injection support.
"""

from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod

from common.logger import get_logger
from common.exceptions import WorkflowError, ConfigurationError
from common.pattern.cor.handler import Handler
from common.di.container import get_container
from domain.handler.newcase_handler import NewCaseHandler
from domain.handler.inprocesscase_handler import InprogressCaseHandler
from domain.handler.finishedcase_handler import FinishedCaseHandler
from domain.handler.default_handler import DefaultHandler

logger = get_logger(__name__)


class HandlerFactory(ABC):
    """
    Abstract factory for creating workflow handlers.
    
    This factory provides an abstraction for creating handler chains,
    enabling better testability and flexibility.
    """
    
    @abstractmethod
    def create_handler_chain(self) -> Handler:
        """
        Create a workflow handler chain.
        
        Returns:
            Handler chain starting with the first handler
            
        Raises:
            WorkflowError: If handler creation fails
        """
        pass


class DefaultHandlerFactory(HandlerFactory):
    """
    Default implementation of handler factory.
    
    This factory creates the standard handler chain used in production:
    FinishedCaseHandler -> InprogressCaseHandler -> NewCaseHandler -> DefaultHandler
    """
    
    def create_handler_chain(self) -> Handler:
        """
        Create the default workflow handler chain.
        
        Returns:
            Handler chain starting with FinishedCaseHandler
            
        Raises:
            WorkflowError: If handler creation fails
        """
        try:
            logger.debug("Creating default handler chain")
            
            # Create handlers in reverse order (chain backwards)
            default_handler = DefaultHandler()
            new_case_handler = NewCaseHandler()
            inprogress_case_handler = InprogressCaseHandler()
            finished_case_handler = FinishedCaseHandler()
            
            # Build chain: finished -> inprogress -> new -> default
            finished_case_handler.set_next(inprogress_case_handler) \
                                  .set_next(new_case_handler) \
                                  .set_next(default_handler)
            
            logger.debug("Handler chain created successfully")
            return finished_case_handler
            
        except Exception as e:
            logger.error("Failed to create handler chain", error=str(e), exc_info=True)
            raise WorkflowError(
                f"Failed to create handler chain: {str(e)}",
                error_code="HANDLER_CREATION_ERROR",
                context={'error': str(e)}
            ) from e


class ConfigurableHandlerFactory(HandlerFactory):
    """
    Configurable handler factory that creates handlers based on configuration.
    
    This factory allows for dynamic handler chain creation based on
    configuration data, enabling more flexible workflow setups.
    """
    
    def __init__(self, handler_config: Optional[Dict[str, Any]] = None):
        """
        Initialize configurable handler factory.
        
        Args:
            handler_config: Optional configuration dictionary specifying
                          handler order and types. If None, uses default configuration.
        """
        self.handler_config = handler_config or {
            'handlers': [
                'finished_case',
                'inprogress_case',
                'new_case',
                'default'
            ]
        }
        logger.debug("ConfigurableHandlerFactory initialized", 
                    config=self.handler_config)
    
    def _create_handler(self, handler_type: str) -> Handler:
        """
        Create a handler instance by type.
        
        Args:
            handler_type: Handler type identifier
            
        Returns:
            Handler instance
            
        Raises:
            WorkflowError: If handler type is unknown
        """
        handler_map = {
            'finished_case': FinishedCaseHandler,
            'inprogress_case': InprogressCaseHandler,
            'new_case': NewCaseHandler,
            'default': DefaultHandler,
        }
        
        if handler_type not in handler_map:
            logger.error("Unknown handler type", handler_type=handler_type)
            raise WorkflowError(
                f"Unknown handler type: {handler_type}",
                error_code="UNKNOWN_HANDLER_TYPE",
                context={'handler_type': handler_type, 'available_types': list(handler_map.keys())}
            )
        
        handler_class = handler_map[handler_type]
        logger.debug("Creating handler", handler_type=handler_type)
        return handler_class()
    
    def create_handler_chain(self) -> Handler:
        """
        Create handler chain based on configuration.
        
        Returns:
            Handler chain starting with first configured handler
            
        Raises:
            WorkflowError: If handler creation fails
        """
        try:
            handlers_config = self.handler_config.get('handlers', [])
            
            if not handlers_config:
                logger.warning("No handlers in configuration, using default factory")
                default_factory = DefaultHandlerFactory()
                return default_factory.create_handler_chain()
            
            logger.debug("Creating handler chain from configuration", 
                        handlers=handlers_config)
            
            # Create handlers
            handlers = [self._create_handler(h) for h in handlers_config]
            
            # Build chain backwards (last handler points to next)
            for i in range(len(handlers) - 1):
                handlers[i].set_next(handlers[i + 1])
            
            first_handler = handlers[0]
            logger.debug("Handler chain created from configuration",
                        handlers_count=len(handlers))
            return first_handler
            
        except WorkflowError:
            raise
        except Exception as e:
            logger.error("Failed to create configurable handler chain", 
                        error=str(e), exc_info=True)
            raise WorkflowError(
                f"Failed to create configurable handler chain: {str(e)}",
                error_code="HANDLER_CREATION_ERROR",
                context={'error': str(e), 'config': self.handler_config}
            ) from e


class RuleEngineFactory:
    """
    Factory for creating rule engine components.
    
    This factory creates rule engine components with proper dependency injection,
    enabling better testability and separation of concerns.
    """
    
    def __init__(self, container=None):
        """
        Initialize rule engine factory.
        
        Args:
            container: Optional DI container. If None, uses global container.
        """
        self.container = container or get_container()
        logger.debug("RuleEngineFactory initialized")
    
    def create_handler_factory(self, 
                              config: Optional[Dict[str, Any]] = None) -> HandlerFactory:
        """
        Create a handler factory based on configuration.
        
        Args:
            config: Optional handler configuration. If None, uses default factory.
            
        Returns:
            HandlerFactory instance
        """
        if config and 'handlers' in config:
            logger.debug("Creating configurable handler factory", config=config)
            return ConfigurableHandlerFactory(handler_config=config)
        else:
            logger.debug("Creating default handler factory")
            return DefaultHandlerFactory()
    
    def get_handler_chain(self, 
                         config: Optional[Dict[str, Any]] = None) -> Handler:
        """
        Get a handler chain instance.
        
        This method uses the DI container to get or create handler chains,
        enabling singleton behavior if configured.
        
        Args:
            config: Optional handler configuration
            
        Returns:
            Handler chain instance
        """
        # Use DI container to manage handler chain lifecycle
        cache_key = 'handler_chain'
        
        if not self.container.has(cache_key):
            handler_factory = self.create_handler_factory(config)
            self.container.register(
                cache_key,
                lambda: handler_factory.create_handler_chain(),
                singleton=True
            )
        
        return self.container.get(cache_key)


def get_handler_factory(config: Optional[Dict[str, Any]] = None) -> HandlerFactory:
    """
    Get a handler factory instance (convenience function).
    
    Args:
        config: Optional handler configuration
        
    Returns:
        HandlerFactory instance
    """
    factory = RuleEngineFactory()
    return factory.create_handler_factory(config)

