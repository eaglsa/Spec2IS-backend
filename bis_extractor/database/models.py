from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, JSON
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class CrawlLog(Base):
    __tablename__ = 'crawl_log'
    id = Column(Integer, primary_key=True)
    url = Column(String, unique=True, index=True)
    entity_type = Column(String)  # e.g., 'department', 'standard', 'detail'
    status = Column(String)       # 'pending', 'processing', 'completed', 'failed'
    retry_count = Column(Integer, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    error_message = Column(Text, nullable=True)
    raw_file_path = Column(String, nullable=True)

class ErrorLog(Base):
    __tablename__ = 'errors'
    id = Column(Integer, primary_key=True)
    url = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    error = Column(Text)
    action = Column(String)

class Department(Base):
    __tablename__ = 'departments'
    id = Column(Integer, primary_key=True)
    department_id = Column(String, unique=True, index=True)
    name = Column(String)
    url = Column(String)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    standards = relationship('Standard', back_populates='department')

class Standard(Base):
    __tablename__ = 'standards'
    id = Column(Integer, primary_key=True)
    department_id = Column(String, ForeignKey('departments.department_id'))
    is_number = Column(String, index=True)
    year = Column(String)
    title = Column(Text)
    status = Column(String)
    url = Column(String)
    detail_url = Column(String)
    encrypted_id = Column(String, nullable=True)
    bis_standard_id = Column(Integer, nullable=True)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    
    department = relationship('Department', back_populates='standards')
    details = relationship('StandardDetail', uselist=False, back_populates='standard')
    documents = relationship('Document', back_populates='standard')

class StandardDetail(Base):
    __tablename__ = 'standard_details'
    id = Column(Integer, primary_key=True)
    standard_id = Column(Integer, ForeignKey('standards.id'), unique=True)
    division = Column(String)
    technical_committee = Column(String)
    committee_number = Column(String)
    member_secretary = Column(String)
    standard_type = Column(String)
    language = Column(String)
    certification_status = Column(String)
    mandatory_status = Column(String)
    reaffirmation = Column(String)
    revision = Column(String)
    amendment = Column(String)
    supersedes = Column(String)
    superseded_by = Column(String)
    degree_of_equivalence = Column(String)
    group = Column(String)
    sub_group = Column(String)
    ministry = Column(String)
    sdg = Column(String)
    short_title = Column(String)
    ics_code = Column(String)
    equivalent_standard = Column(String)
    identical_standard = Column(String)
    summary = Column(Text)
    scope = Column(Text)
    publication_date = Column(String)
    effective_date = Column(String)
    withdrawal_date = Column(String)
    classification = Column(String)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    extra_fields = Column(JSON, nullable=True)

    standard = relationship('Standard', back_populates='details')

class Document(Base):
    __tablename__ = 'documents'
    id = Column(Integer, primary_key=True)
    standard_id = Column(Integer, ForeignKey('standards.id'))
    name = Column(String)
    document_type = Column(String)
    category = Column(String)
    url = Column(String)
    file_extension = Column(String)
    file_size = Column(String)
    publication_date = Column(String)
    description = Column(Text)
    document_id = Column(String)
    local_path = Column(String)
    extraction_status = Column(String) # 'pending', 'extracted', 'failed', 'encrypted'
    scraped_at = Column(DateTime, default=datetime.utcnow)

    standard = relationship('Standard', back_populates='documents')
    
class StandardRelationship(Base):
    __tablename__ = 'standard_relationships'
    id = Column(Integer, primary_key=True)
    source_standard_id = Column(Integer, ForeignKey('standards.id'))
    target_standard_is_number = Column(String)
    relationship_type = Column(String) # 'refers_to', 'amended_by', 'supersedes', 'superseded_by'
    raw_relationship_text = Column(Text)
