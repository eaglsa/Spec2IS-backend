from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from bis_extractor.database.models import CrawlLog, Department, Standard, StandardDetail, Document, StandardRelationship

class Repository:
    def __init__(self, session: Session):
        self.session = session

    def add_crawl_log(self, url: str, entity_type: str):
        log = self.session.query(CrawlLog).filter_by(url=url).first()
        if not log:
            log = CrawlLog(url=url, entity_type=entity_type, status='pending')
            self.session.add(log)
            self.session.commit()
        return log

    def update_crawl_log(self, url: str, status: str, error_message: str = None, raw_path: str = None):
        log = self.session.query(CrawlLog).filter_by(url=url).first()
        if log:
            log.status = status
            if error_message:
                log.error_message = error_message
            if raw_path:
                log.raw_file_path = raw_path
            self.session.commit()

    def get_pending_logs(self, entity_type: str):
        return self.session.query(CrawlLog).filter_by(entity_type=entity_type, status='pending').all()

    def add_department(self, department_id: str, name: str, url: str):
        dept = self.session.query(Department).filter_by(department_id=department_id).first()
        if not dept:
            dept = Department(department_id=department_id, name=name, url=url)
            self.session.add(dept)
            try:
                self.session.commit()
            except IntegrityError:
                self.session.rollback()
        return dept

    def add_standard(self, dept_id: str, is_number: str, year: str, title: str, status: str, url: str, detail_url: str, encrypted_id: str = None, bis_standard_id: int = None):
        # Deterministic upsert
        if bis_standard_id:
            std = self.session.query(Standard).filter_by(bis_standard_id=bis_standard_id).first()
        else:
            std = self.session.query(Standard).filter_by(is_number=is_number, year=year).first()
            
        if not std:
            std = Standard(
                department_id=dept_id,
                is_number=is_number,
                year=year,
                title=title,
                status=status,
                url=url,
                detail_url=detail_url,
                encrypted_id=encrypted_id,
                bis_standard_id=bis_standard_id
            )
            self.session.add(std)
        else:
            std.title = title
            std.status = status
            if encrypted_id:
                std.encrypted_id = encrypted_id
            if bis_standard_id:
                std.bis_standard_id = bis_standard_id
                
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
        return std

    def add_standard_detail(self, standard_id: int, data: dict):
        detail = self.session.query(StandardDetail).filter_by(standard_id=standard_id).first()
        if not detail:
            detail = StandardDetail(standard_id=standard_id, **data)
            self.session.add(detail)
            try:
                self.session.commit()
            except IntegrityError:
                self.session.rollback()
        else:
            for key, value in data.items():
                setattr(detail, key, value)
            self.session.commit()
        return detail

    def add_document(self, standard_id: int, doc_data: dict):
        doc = self.session.query(Document).filter_by(url=doc_data.get('url')).first()
        if not doc:
            doc = Document(standard_id=standard_id, **doc_data)
            self.session.add(doc)
            try:
                self.session.commit()
            except IntegrityError:
                self.session.rollback()
        return doc

    def add_relationship(self, source_id: int, target_is: str, rel_type: str, raw_text: str = None):
        rel = self.session.query(StandardRelationship).filter_by(
            source_standard_id=source_id, 
            target_standard_is_number=target_is, 
            relationship_type=rel_type
        ).first()
        if not rel:
            rel = StandardRelationship(
                source_standard_id=source_id, 
                target_standard_is_number=target_is, 
                relationship_type=rel_type,
                raw_relationship_text=raw_text
            )
            self.session.add(rel)
            try:
                self.session.commit()
            except IntegrityError:
                self.session.rollback()
        return rel
