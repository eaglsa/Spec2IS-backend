"""
SQLAlchemy ORM models that mirror the updated PostgreSQL schema.
Tier 1: Core Standard Metadata (Normalized)
Tier 2: Metadata Provenance & Audit
Tier 3: Future Technical & Semantic Enrichment
"""
from __future__ import annotations

import datetime
from typing import List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Tier 1: Core Standard Metadata
# ---------------------------------------------------------------------------


class StandardDomain(Base):
    """Tier 1.1: Look-up table to prevent duplication of domain titles."""
    __tablename__ = "standard_domains"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True))

    standards: Mapped[List["Standard"]] = relationship(
        "Standard", back_populates="domain"
    )


class Standard(Base):
    """Tier 1.2: Enduring identity of an Indian Standard."""
    __tablename__ = "standards"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    standard_number: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    domain_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("standard_domains.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text)
    committee_designation: Mapped[Optional[str]] = mapped_column(String(255))
    verification_status: Mapped[Optional[str]] = mapped_column(String(100))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    domain: Mapped[Optional[StandardDomain]] = relationship(
        "StandardDomain", back_populates="standards"
    )
    versions: Mapped[List["StandardVersion"]] = relationship(
        "StandardVersion", back_populates="standard"
    )
    keywords: Mapped[List["StandardKeyword"]] = relationship(
        "StandardKeyword",
        secondary="standard_keyword_map",
        back_populates="standards",
    )
    parameters: Mapped[List["StandardParameter"]] = relationship(
        "StandardParameter", back_populates="standard"
    )
    sources: Mapped[List["StandardSource"]] = relationship(
        "StandardSource", back_populates="standard"
    )
    embeddings: Mapped[List["StandardEmbedding"]] = relationship(
        "StandardEmbedding", back_populates="standard"
    )


class StandardVersion(Base):
    """Tier 1.3: Revision instances of a standard."""
    __tablename__ = "standard_versions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    standard_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("standards.id", ondelete="CASCADE"), nullable=False
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    edition: Mapped[Optional[str]] = mapped_column(String(255))
    status: Mapped[Optional[str]] = mapped_column(String(100))
    revision_description: Mapped[Optional[str]] = mapped_column(Text)
    effective_date: Mapped[Optional[datetime.date]] = mapped_column(Date)
    verification_status: Mapped[Optional[str]] = mapped_column(String(100))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    standard: Mapped["Standard"] = relationship("Standard", back_populates="versions")
    parts: Mapped[List["StandardPart"]] = relationship(
        "StandardPart", back_populates="version"
    )


class StandardPart(Base):
    """Tier 1.4: Multi-part standards under a version."""
    __tablename__ = "standard_parts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    standard_version_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("standard_versions.id", ondelete="CASCADE"), nullable=False
    )
    part_number: Mapped[str] = mapped_column(String(50), nullable=False)
    part_title: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    version: Mapped["StandardVersion"] = relationship(
        "StandardVersion", back_populates="parts"
    )


class StandardRelationship(Base):
    """Tier 1.5: Graph linking revisions and related standards."""
    __tablename__ = "standard_relationships"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_standard_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("standards.id", ondelete="CASCADE"), nullable=False
    )
    source_version_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("standard_versions.id", ondelete="SET NULL")
    )
    target_standard_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("standards.id", ondelete="SET NULL")
    )
    target_version_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("standard_versions.id", ondelete="SET NULL")
    )
    relationship_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # REVISES | REVISED_BY | SUPERSEDES | SUPERSEDED_BY | RELATED_TO | WITHDRAWN | OTHER
    target_standard_number_raw: Mapped[Optional[str]] = mapped_column(String(100))
    notes: Mapped[Optional[str]] = mapped_column(Text)


class StandardKeyword(Base):
    """Tier 1.6a: Normalized keywords table."""
    __tablename__ = "standard_keywords"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    keyword: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    standards: Mapped[List["Standard"]] = relationship(
        "Standard",
        secondary="standard_keyword_map",
        back_populates="keywords",
    )


class StandardKeywordMap(Base):
    """Tier 1.6b: Many-to-many relationship map."""
    __tablename__ = "standard_keyword_map"

    standard_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("standards.id", ondelete="CASCADE"), primary_key=True
    )
    keyword_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("standard_keywords.id", ondelete="CASCADE"), primary_key=True
    )


# ---------------------------------------------------------------------------
# Tier 2: Metadata Provenance & Audit
# ---------------------------------------------------------------------------


class StandardSource(Base):
    """Tier 2.7: Provenance tracking for standard metadata."""
    __tablename__ = "standard_sources"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    standard_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("standards.id", ondelete="CASCADE"), nullable=False
    )
    standard_version_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("standard_versions.id", ondelete="SET NULL")
    )
    source_name: Mapped[Optional[str]] = mapped_column(Text)
    source_url: Mapped[Optional[str]] = mapped_column(Text)
    source_type: Mapped[Optional[str]] = mapped_column(String(100))
    provenance_text: Mapped[str] = mapped_column(Text, nullable=False)
    verification_status: Mapped[Optional[str]] = mapped_column(String(100))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    standard: Mapped[Optional["Standard"]] = relationship(
        "Standard", back_populates="sources"
    )


# ---------------------------------------------------------------------------
# Tier 3: Technical & Semantic Enrichment
# ---------------------------------------------------------------------------


class StandardParameter(Base):
    """Tier 3.8: Technical parameters, thresholds, and flows."""
    __tablename__ = "standard_parameters"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    standard_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("standards.id", ondelete="CASCADE"), nullable=False
    )
    standard_version_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("standard_versions.id", ondelete="SET NULL")
    )
    parameter_name: Mapped[str] = mapped_column(String(255), nullable=False)
    parameter_value: Mapped[str] = mapped_column(Text, nullable=False)
    unit: Mapped[Optional[str]] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(Text)
    source_text: Mapped[Optional[str]] = mapped_column(Text)

    standard: Mapped[Optional["Standard"]] = relationship(
        "Standard", back_populates="parameters"
    )


class StandardEmbedding(Base):
    """Tier 3.9: Vector embeddings powered by pgvector."""
    __tablename__ = "standard_embeddings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    standard_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("standards.id", ondelete="CASCADE"), nullable=False
    )
    standard_version_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("standard_versions.id", ondelete="SET NULL")
    )
    embedding: Mapped[Optional[list]] = mapped_column(Vector(384), nullable=True)
    embedding_model: Mapped[Optional[str]] = mapped_column(String(100))
    text_content: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True))

    standard: Mapped[Optional["Standard"]] = relationship(
        "Standard", back_populates="embeddings"
    )
