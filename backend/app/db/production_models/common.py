"""Shared production-schema column and constraint helpers."""

from __future__ import annotations

from sqlalchemy import BigInteger, CheckConstraint, Column, DateTime, Integer, Text, text
from sqlalchemy.dialects.postgresql import JSONB


SHA256_SQL = "VALUE ~ '^[0-9a-f]{64}$'"
PATH_SQL = (
    "VALUE <> '' AND VALUE !~ '^/' AND VALUE !~ '(^|/)\\.\\.(/|$)' "
    "AND position(chr(92) in VALUE) = 0"
)


def created_at() -> Column[DateTime]:
    return Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()"))


def updated_at() -> Column[DateTime]:
    return Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("now()"))


def json_object(name: str, *, nullable: bool = False) -> Column[JSONB]:
    return Column(name, JSONB, nullable=nullable, server_default=text("'{}'::jsonb"))


def json_array(name: str, *, nullable: bool = False) -> Column[JSONB]:
    return Column(name, JSONB, nullable=nullable, server_default=text("'[]'::jsonb"))


def json_type_check(column: str, kind: str, name: str) -> CheckConstraint:
    return CheckConstraint(f"jsonb_typeof({column}) = '{kind}'", name=name)


def prefix_check(column: str, prefix: str, name: str) -> CheckConstraint:
    return CheckConstraint(f"{column} LIKE '{prefix}%'", name=name)


def sha256_check(column: str, name: str, *, nullable: bool = False) -> CheckConstraint:
    expression = f"{column} ~ '^[0-9a-f]{{64}}$'"
    if nullable:
        expression = f"{column} IS NULL OR ({expression})"
    return CheckConstraint(expression, name=name)


def nonnegative(column: str, name: str) -> CheckConstraint:
    return CheckConstraint(f"{column} >= 0", name=name)


def positive(column: str, name: str) -> CheckConstraint:
    return CheckConstraint(f"{column} > 0", name=name)


def paired(left: str, right: str, name: str) -> CheckConstraint:
    return CheckConstraint(f"({left} IS NULL) = ({right} IS NULL)", name=name)


def range_check(start: str, end: str, name: str, *, nullable: bool = False) -> CheckConstraint:
    expression = f"{start} > 0 AND {end} >= {start}"
    if nullable:
        expression = f"({start} IS NULL AND {end} IS NULL) OR ({expression})"
    return CheckConstraint(expression, name=name)


def producer_columns() -> tuple[Column[Text], ...]:
    return (
        Column("producer_stage", Text, nullable=False),
        Column("producer_name", Text, nullable=False),
        Column("producer_version", Text, nullable=False),
    )


def support_columns() -> tuple[Column, ...]:
    from sqlalchemy import Float

    return (
        Column("support_type", Text, nullable=False),
        Column("confidence", Float),
        json_array("diagnostic_ids"),
        CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="confidence_range"),
        json_type_check("diagnostic_ids", "array", "diagnostic_ids_array"),
    )


def versioned_identity(prefix: str) -> tuple[Column, ...]:
    return (
        Column("id", Text, primary_key=True),
        Column("repository_id", Text, nullable=False),
        Column("index_version_id", Text, nullable=False),
        Column("canonical_key", Text, nullable=False),
        prefix_check("id", prefix, "id_prefix"),
    )
