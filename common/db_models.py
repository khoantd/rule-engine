"""
Database models for Rule Engine.

This module defines SQLAlchemy ORM models for:
- Rulesets (collections of rules)
- Rules (individual business rules)
- Conditions (rule conditions)
- Actions (rule actions)
- Pattern: one actionset entry (API exposes ruleset's list as "actionset")
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Index,
    CheckConstraint,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    validates,
)
from sqlalchemy.ext.hybrid import hybrid_property

from common.logger import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class RuleStatus(str, Enum):
    """Rule lifecycle status."""

    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class ConditionOperator(str, Enum):
    """Supported condition operators."""

    EQUAL = "equal"
    NOT_EQUAL = "not_equal"
    GREATER_THAN = "greater_than"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    LESS_THAN = "less_than"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"
    IN = "in"
    NOT_IN = "not_in"
    RANGE = "range"
    CONTAINS = "contains"
    REGEX = "regex"


class Ruleset(Base):
    """
    Ruleset model.

    A ruleset is a collection of related rules that can be executed together.
    Supports versioning and multi-tenancy.
    """

    __tablename__ = "rulesets"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0")
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=RuleStatus.ACTIVE.value
    )
    tenant_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    updated_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # JSON fields for flexible configuration
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    extra_metadata: Mapped[Optional[dict]] = mapped_column(
        "metadata", JSON, nullable=True
    )

    # Relationships (patterns = actionset entries for this ruleset)
    rules: Mapped[List["Rule"]] = relationship(
        "Rule", back_populates="ruleset", cascade="all, delete-orphan", lazy="dynamic"
    )
    patterns: Mapped[List["Pattern"]] = relationship(
        "Pattern", back_populates="ruleset", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_rulesets_status", "status"),
        Index("idx_rulesets_version", "version"),
        CheckConstraint("version != ''", name="check_ruleset_version_not_empty"),
    )

    @validates("name")
    def validate_name(self, key, name):
        if not name or not name.strip():
            raise ValueError("Ruleset name cannot be empty")
        return name.strip()

    @hybrid_property
    def is_active(self) -> bool:
        return self.status == RuleStatus.ACTIVE.value

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "status": self.status,
            "tenant_id": self.tenant_id,
            "is_default": self.is_default,
            "tags": self.tags,
            "metadata": self.extra_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
            "updated_by": self.updated_by,
            "rule_count": self.rules.count() if hasattr(self.rules, "count") else 0,
            "actionset_count": len(self.patterns) if self.patterns else 0,
        }


class Rule(Base):
    """
    Rule model.

    Represents a single business rule with conditions and actions.
    """

    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    rule_name: Mapped[str] = mapped_column(String(255), nullable=False)
    attribute: Mapped[str] = mapped_column(String(255), nullable=False)
    condition: Mapped[str] = mapped_column(String(50), nullable=False)
    constant: Mapped[str] = mapped_column(Text, nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Scoring
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    rule_point: Mapped[int] = mapped_column(Integer, default=0)
    priority: Mapped[int] = mapped_column(Integer, default=0)

    # Action result
    action_result: Mapped[str] = mapped_column(String(10), nullable=False)

    # Status and version
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=RuleStatus.ACTIVE.value
    )
    version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0")

    # Foreign key to ruleset
    ruleset_id: Mapped[int] = mapped_column(
        ForeignKey("rulesets.id", ondelete="CASCADE"), nullable=False
    )

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    updated_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # JSON fields for flexible configuration
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    extra_metadata: Mapped[Optional[dict]] = mapped_column(
        "metadata", JSON, nullable=True
    )

    # Relationships
    ruleset: Mapped["Ruleset"] = relationship("Ruleset", back_populates="rules")

    # Indexes
    __table_args__ = (
        Index("idx_rules_rule_id", "rule_id"),
        Index("idx_rules_attribute", "attribute"),
        Index("idx_rules_priority", "priority"),
        Index("idx_rules_status", "status"),
        Index("idx_rules_ruleset", "ruleset_id", "priority"),
        CheckConstraint("weight >= 0", name="check_weight_non_negative"),
        CheckConstraint("rule_point >= 0", name="check_rule_point_non_negative"),
    )

    @validates("rule_id")
    def validate_rule_id(self, key, rule_id):
        if not rule_id or not rule_id.strip():
            raise ValueError("Rule ID cannot be empty")
        return rule_id.strip()

    @validates("condition")
    def validate_condition(self, key, condition):
        try:
            ConditionOperator(condition)
        except ValueError:
            raise ValueError(f"Invalid condition operator: {condition}")
        return condition

    @hybrid_property
    def is_active(self) -> bool:
        return self.status == RuleStatus.ACTIVE.value

    @hybrid_property
    def calculated_points(self) -> float:
        """Calculate weighted points."""
        return self.rule_point * self.weight

    def to_dict(self, include_ruleset: bool = False) -> dict:
        """Convert model to dictionary."""
        result = {
            "id": self.id,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "attribute": self.attribute,
            "condition": self.condition,
            "constant": self.constant,
            "message": self.message,
            "weight": self.weight,
            "rule_point": self.rule_point,
            "priority": self.priority,
            "action_result": self.action_result,
            "status": self.status,
            "version": self.version,
            "ruleset_id": self.ruleset_id,
            "tags": self.tags,
            "metadata": self.extra_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
            "updated_by": self.updated_by,
            "calculated_points": self.calculated_points,
        }

        if include_ruleset and self.ruleset:
            result["ruleset"] = self.ruleset.to_dict()

        return result


class Condition(Base):
    """
    Condition model.

    Represents reusable condition definitions that can be shared across rules.
    """

    __tablename__ = "conditions"

    id: Mapped[int] = mapped_column(primary_key=True)
    condition_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attribute: Mapped[str] = mapped_column(String(255), nullable=False)
    operator: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)

    # Status
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=RuleStatus.ACTIVE.value
    )

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    updated_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # JSON fields
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    extra_metadata: Mapped[Optional[dict]] = mapped_column(
        "metadata", JSON, nullable=True
    )

    # Indexes
    __table_args__ = (
        Index("idx_conditions_condition_id", "condition_id"),
        Index("idx_conditions_attribute", "attribute"),
        Index("idx_conditions_status", "status"),
    )

    @validates("operator")
    def validate_operator(self, key, operator):
        try:
            ConditionOperator(operator)
        except ValueError:
            raise ValueError(f"Invalid condition operator: {operator}")
        return operator

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "condition_id": self.condition_id,
            "name": self.name,
            "description": self.description,
            "attribute": self.attribute,
            "operator": self.operator,
            "value": self.value,
            "status": self.status,
            "tags": self.tags,
            "metadata": self.extra_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
            "updated_by": self.updated_by,
        }


class Attribute(Base):
    """
    Attribute (fact) model.

    Represents reusable attribute/fact definitions that can be referenced
    by conditions. The attribute_id is the key used in input data and
    in condition definitions (e.g. "issue", "title", "age_till_now").
    """

    __tablename__ = "attributes"

    id: Mapped[int] = mapped_column(primary_key=True)
    attribute_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    data_type: Mapped[str] = mapped_column(String(50), nullable=False, default="string")

    # Status
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=RuleStatus.ACTIVE.value
    )

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    updated_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # JSON fields
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    extra_metadata: Mapped[Optional[dict]] = mapped_column(
        "metadata", JSON, nullable=True
    )

    # Indexes
    __table_args__ = (
        Index("idx_attributes_attribute_id", "attribute_id"),
        Index("idx_attributes_data_type", "data_type"),
        Index("idx_attributes_status", "status"),
    )

    @validates("attribute_id")
    def validate_attribute_id(self, key, attribute_id):
        if not attribute_id or not attribute_id.strip():
            raise ValueError("Attribute ID cannot be empty")
        return attribute_id.strip()

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "attribute_id": self.attribute_id,
            "name": self.name,
            "description": self.description,
            "data_type": self.data_type,
            "status": self.status,
            "tags": self.tags,
            "metadata": self.extra_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
            "updated_by": self.updated_by,
        }


class Action(Base):
    """
    Action model.

    Represents reusable action definitions that can be shared across rules.
    May be linked to a pattern (one pattern has many actions).
    """

    __tablename__ = "actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    action_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    configuration: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Status
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=RuleStatus.ACTIVE.value
    )

    # Foreign key to pattern (one pattern has many actions)
    pattern_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("patterns.id", ondelete="CASCADE"), nullable=True, index=True
    )

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    updated_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # JSON fields
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    extra_metadata: Mapped[Optional[dict]] = mapped_column(
        "metadata", JSON, nullable=True
    )

    # Relationships
    pattern: Mapped[Optional["Pattern"]] = relationship(
        "Pattern", back_populates="actions"
    )

    # Indexes
    __table_args__ = (
        Index("idx_actions_action_id", "action_id"),
        Index("idx_actions_action_type", "action_type"),
        Index("idx_actions_status", "status"),
    )

    def to_dict(self, include_pattern: bool = False) -> dict:
        """Convert model to dictionary."""
        result = {
            "id": self.id,
            "action_id": self.action_id,
            "name": self.name,
            "description": self.description,
            "action_type": self.action_type,
            "configuration": self.configuration,
            "status": self.status,
            "pattern_id": self.pattern_id,
            "tags": self.tags,
            "metadata": self.extra_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
            "updated_by": self.updated_by,
        }
        if include_pattern and self.pattern:
            result["pattern"] = self.pattern.to_dict()
        return result


class Pattern(Base):
    """
    One actionset entry (table: patterns).

    API exposes a ruleset's actionset as a list of pattern keys or entries.
    Maps pattern_key (e.g., "YYY", "Y--") to action_recommendation.
    """

    __tablename__ = "patterns"

    id: Mapped[int] = mapped_column(primary_key=True)
    pattern_key: Mapped[str] = mapped_column(String(50), nullable=False)
    action_recommendation: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Foreign key to ruleset
    ruleset_id: Mapped[int] = mapped_column(
        ForeignKey("rulesets.id", ondelete="CASCADE"), nullable=False
    )

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Unique constraint for pattern key within a ruleset
    __table_args__ = (
        Index("idx_patterns_ruleset", "ruleset_id"),
        Index("idx_patterns_key", "pattern_key"),
    )

    # Relationships
    ruleset: Mapped["Ruleset"] = relationship("Ruleset", back_populates="patterns")
    actions: Mapped[List["Action"]] = relationship(
        "Action", back_populates="pattern", cascade="all, delete-orphan"
    )

    @validates("pattern_key")
    def validate_pattern_key(self, key, pattern_key):
        if not pattern_key or not pattern_key.strip():
            raise ValueError("Pattern key cannot be empty")
        return pattern_key.strip()

    def to_dict(
        self, include_ruleset: bool = False, include_actions: bool = False
    ) -> dict:
        """Convert model to dictionary."""
        result = {
            "id": self.id,
            "pattern_key": self.pattern_key,
            "action_recommendation": self.action_recommendation,
            "description": self.description,
            "ruleset_id": self.ruleset_id,
            "action_count": len(self.actions) if self.actions else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_ruleset and self.ruleset:
            result["ruleset"] = self.ruleset.to_dict()
        if include_actions and self.actions:
            result["actions"] = [a.to_dict() for a in self.actions]

        return result


class ExecutionLog(Base):
    """
    Execution log model.

    Logs rule execution events for debugging and analytics.
    Stored as time-series data in TimescaleDB.
    """

    __tablename__ = "execution_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    execution_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Input/output
    input_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    output_data: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Execution details
    ruleset_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_points: Mapped[float] = mapped_column(Float, nullable=True)
    pattern_result: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    execution_time_ms: Mapped[float] = mapped_column(Float, nullable=False)

    # A/B Test tracking
    ab_test_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, index=True
    )
    ab_test_variant: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Metadata
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamp (important for TimescaleDB time-series)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )

    # Indexes for time-series queries
    __table_args__ = (
        Index("idx_execution_logs_timestamp", "timestamp"),
        Index("idx_execution_logs_execution_id", "execution_id"),
        Index("idx_execution_logs_success", "success"),
        Index("idx_execution_logs_ab_test", "ab_test_id", "ab_test_variant"),
    )

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "execution_id": self.execution_id,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "ruleset_id": self.ruleset_id,
            "total_points": self.total_points,
            "pattern_result": self.pattern_result,
            "execution_time_ms": self.execution_time_ms,
            "ab_test_id": self.ab_test_id,
            "ab_test_variant": self.ab_test_variant,
            "success": self.success,
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class RuleVersion(Base):
    """
    Rule Version model.

    Tracks historical versions of rules for rollback and comparison.
    Every time a rule is modified, a new version is automatically created.
    """

    __tablename__ = "rule_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Rule snapshot (stores complete rule state)
    rule_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    rule_name: Mapped[str] = mapped_column(String(255), nullable=False)
    attribute: Mapped[str] = mapped_column(String(255), nullable=False)
    condition: Mapped[str] = mapped_column(String(50), nullable=False)
    constant: Mapped[str] = mapped_column(Text, nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Scoring
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    rule_point: Mapped[int] = mapped_column(Integer, default=0)
    priority: Mapped[int] = mapped_column(Integer, default=0)

    # Action result
    action_result: Mapped[str] = mapped_column(String(10), nullable=False)

    # Status and version
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=RuleStatus.ACTIVE.value
    )
    version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0")

    # Foreign key to ruleset
    ruleset_id: Mapped[int] = mapped_column(
        ForeignKey("rulesets.id", ondelete="CASCADE"), nullable=False
    )

    # Version metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    change_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)

    # JSON fields
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    extra_metadata: Mapped[Optional[dict]] = mapped_column(
        "metadata", JSON, nullable=True
    )

    # Indexes
    __table_args__ = (
        Index("idx_rule_versions_rule_id", "rule_id", "version_number"),
        Index("idx_rule_versions_ruleset", "ruleset_id", "version_number"),
        Index("idx_rule_versions_is_current", "is_current"),
        CheckConstraint("weight >= 0", name="check_rule_version_weight_non_negative"),
        CheckConstraint(
            "rule_point >= 0", name="check_rule_version_point_non_negative"
        ),
    )

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "version_number": self.version_number,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "attribute": self.attribute,
            "condition": self.condition,
            "constant": self.constant,
            "message": self.message,
            "weight": self.weight,
            "rule_point": self.rule_point,
            "priority": self.priority,
            "action_result": self.action_result,
            "status": self.status,
            "version": self.version,
            "ruleset_id": self.ruleset_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by,
            "change_reason": self.change_reason,
            "is_current": self.is_current,
            "tags": self.tags,
            "metadata": self.extra_metadata,
        }


class RuleABTest(Base):
    """
    Rule A/B Test model.

    Manages A/B testing experiments for rules, allowing comparison between
    different rule versions or configurations.
    """

    __tablename__ = "rule_ab_tests"

    id: Mapped[int] = mapped_column(primary_key=True)
    test_id: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    test_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Target rule
    rule_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ruleset_id: Mapped[int] = mapped_column(
        ForeignKey("rulesets.id", ondelete="CASCADE"), nullable=False
    )

    # Test configuration
    traffic_split_a: Mapped[float] = mapped_column(Float, default=0.5)
    traffic_split_b: Mapped[float] = mapped_column(Float, default=0.5)

    # Variant A (control)
    variant_a_version: Mapped[str] = mapped_column(String(50), nullable=False)
    variant_a_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Variant B (treatment)
    variant_b_version: Mapped[str] = mapped_column(String(50), nullable=False)
    variant_b_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Test status
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")

    # Test timing
    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_hours: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Sample size
    min_sample_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    confidence_level: Mapped[float] = mapped_column(Float, default=0.95)

    # Results
    winning_variant: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    statistical_significance: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # JSON fields
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    extra_metadata: Mapped[Optional[dict]] = mapped_column(
        "metadata", JSON, nullable=True
    )

    # Indexes
    __table_args__ = (
        Index("idx_rule_ab_tests_rule_id", "rule_id"),
        Index("idx_rule_ab_tests_status", "status"),
        Index("idx_rule_ab_tests_timing", "start_time", "end_time"),
        CheckConstraint(
            "traffic_split_a >= 0 and traffic_split_a <= 1", name="check_split_a_valid"
        ),
        CheckConstraint(
            "traffic_split_b >= 0 and traffic_split_b <= 1", name="check_split_b_valid"
        ),
        CheckConstraint(
            "abs(traffic_split_a + traffic_split_b - 1.0) < 0.01",
            name="check_split_sum",
        ),
        CheckConstraint(
            "confidence_level > 0 and confidence_level <= 1",
            name="check_confidence_level",
        ),
    )

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "test_id": self.test_id,
            "test_name": self.test_name,
            "description": self.description,
            "rule_id": self.rule_id,
            "ruleset_id": self.ruleset_id,
            "traffic_split_a": self.traffic_split_a,
            "traffic_split_b": self.traffic_split_b,
            "variant_a_version": self.variant_a_version,
            "variant_a_description": self.variant_a_description,
            "variant_b_version": self.variant_b_version,
            "variant_b_description": self.variant_b_description,
            "status": self.status,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_hours": self.duration_hours,
            "min_sample_size": self.min_sample_size,
            "confidence_level": self.confidence_level,
            "winning_variant": self.winning_variant,
            "statistical_significance": self.statistical_significance,
            "tags": self.tags,
            "metadata": self.extra_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
        }


class TestAssignment(Base):
    """
    Test Assignment model.

    Tracks which users/requests are assigned to which A/B test variant.
    Ensures consistent assignment using hash-based routing.
    """

    __tablename__ = "test_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    ab_test_id: Mapped[int] = mapped_column(
        ForeignKey("rule_ab_tests.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Assignment key (user ID, session ID, request ID, etc.)
    assignment_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Assigned variant
    variant: Mapped[str] = mapped_column(String(10), nullable=False)

    # Assignment metadata
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Execution tracking
    execution_count: Mapped[int] = mapped_column(Integer, default=0)
    last_execution_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )

    # Indexes
    __table_args__ = (
        Index(
            "idx_test_assignments_test_key", "ab_test_id", "assignment_key", unique=True
        ),
        Index("idx_test_assignments_variant", "ab_test_id", "variant"),
    )

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "ab_test_id": self.ab_test_id,
            "assignment_key": self.assignment_key,
            "variant": self.variant,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "execution_count": self.execution_count,
            "last_execution_at": self.last_execution_at.isoformat()
            if self.last_execution_at
            else None,
        }
