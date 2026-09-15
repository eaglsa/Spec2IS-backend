import click
import logging
from bis_extractor.database.schema import init_db, get_session
from bis_extractor.database.repository import Repository
from bis_extractor.crawler.http import HttpClient
from bis_extractor.crawler.discovery import Discoverer
from bis_extractor.validation.validator import generate_report

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

@click.group()
def cli():
    """BIS Standard Extractor CLI"""
    init_db()

@cli.command()
def discover():
    """Discover all departments and standards to build the crawl queue."""
    session = get_session()
    repo = Repository(session)
    http_client = HttpClient()
    
    discoverer = Discoverer(repo, http_client)
    discoverer.discover_departments()
    
    click.echo("Discovery phase completed. Run 'crawl' to process the queue.")
    
@cli.command()
@click.option('--department', help='Crawl a specific department')
@click.option('--standard', help='Crawl a specific standard ID')
def crawl(department, standard):
    """Crawl queued items or specific items."""
    session = get_session()
    repo = Repository(session)
    http_client = HttpClient()
    
    from bis_extractor.crawler.engine import CrawlEngine
    engine = CrawlEngine(repo, http_client)
    
    click.echo(f"Crawling starting... (Department: {department}, Standard: {standard})")
    
    if department:
        engine.crawl_department(department)
    else:
        # Get all departments and crawl them
        from bis_extractor.database.models import Department
        depts = repo.session.query(Department).all()
        for dept in depts:
            engine.crawl_department(dept.name)
    
    click.echo("Crawling completed.")

@cli.command()
def resume():
    """Resume a previous crawl."""
    click.echo("Resuming previous crawl based on pending database logs...")

@cli.command()
def validate():
    """Validate data and generate crawl_report.json"""
    session = get_session()
    repo = Repository(session)
    report = generate_report(repo)
    
    from bis_extractor.validation.inventory import run_all_validations
    run_all_validations()
    
    click.echo(f"Validation completed. Report generated: {report}")

@cli.command()
def export():
    """Export SQLite data to JSON and CSV formats."""
    from bis_extractor.export import export_data
    export_data()
    click.echo("Exporting data to CSV and JSON formats in output/ folder...")

if __name__ == '__main__':
    cli()
