#!/usr/bin/env python
"""
IdiomsSolitaire - Chinese Idioms Solitaire Tool

A high-performance Chinese idioms solitaire program using SQLite database
for fast querying and random matching.
"""
import random
from pathlib import Path

import structlog
import typer
from pypinyin import pinyin
from pypinyin import Style
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from sqlmodel import create_engine
from sqlmodel import Field
from sqlmodel import func
from sqlmodel import select
from sqlmodel import Session
from sqlmodel import SQLModel

# Initialize rich console and structlog
console = Console()
logger = structlog.get_logger()

# Global variables
_pinyin_cache: dict[str, list[str]] = {}
_engine = None
_DB_FILE = 'db.sqlite3'


class Idiom(SQLModel, table=True):  # type: ignore[call-arg]
    """Idiom model for database."""

    __tablename__ = 'idioms'

    id: int | None = Field(default=None, primary_key=True)
    word: str
    pinyin: str
    meaning: str
    first_pinyin: str
    last_pinyin: str


def get_last_pinyin(word: str) -> str:
    """Get the pinyin of the last character in a word (with caching)."""
    if word in _pinyin_cache:
        return _pinyin_cache[word][-1]

    # Only calculate the last character's pinyin for efficiency
    last_char = word[-1]
    if last_char in _pinyin_cache:
        return _pinyin_cache[last_char][0]

    result = pinyin(last_char, style=Style.NORMAL)[0][0]
    _pinyin_cache[last_char] = [result]
    logger.debug('Calculated pinyin', character=last_char, pinyin=result)
    return result


def init_db(db_file: str | None = None) -> None:
    """Initialize SQLite database connection."""
    global _engine

    if db_file is None:
        db_file = _DB_FILE

    db_path = Path(db_file)
    if not db_path.exists():
        logger.error('Database file not found', file=db_file)
        console.print(
            f"[red]Error:[/red] Database file '{db_file}' not found.",
        )
        raise typer.Exit(code=1)

    try:
        sqlite_url = f"sqlite:///{db_file}"
        _engine = create_engine(sqlite_url, echo=False)

        # Check record count
        with Session(_engine) as session:
            statement = select(func.count(Idiom.id))
            count = session.exec(statement).one()

        logger.info('Database loaded', file=db_file, count=count)
        console.print(
            f"[green]✓[/green] Database loaded: [bold]{count}[/bold] idioms",
        )
    except Exception as e:
        logger.error('Database connection failed', error=str(e))
        console.print(f"[red]Error:[/red] Failed to connect to database: {e}")
        raise typer.Exit(code=1)


def get_all_starts_with(word: str) -> list[tuple[str, str]]:
    """Get all idioms that start with the last character of the given word."""
    last_pinyin = get_last_pinyin(word)
    logger.debug('Searching idioms', last_pinyin=last_pinyin)

    with Session(_engine) as session:
        statement = select(Idiom).where(Idiom.first_pinyin == last_pinyin)
        idioms = session.exec(statement).all()
        results = [(idiom.word, idiom.meaning) for idiom in idioms]

    logger.info('Found matching idioms', count=len(results))
    return results


def guess(word: str) -> tuple[str, str] | None:
    """Get a random idiom that can follow the given idiom."""
    matches = get_all_starts_with(word)

    if not matches:
        logger.warning('No matching idiom found', input_word=word)
        return None

    result = random.choice(matches)
    logger.info('Selected random idiom', word=result[0])
    return result


# Initialize typer app
app = typer.Typer(
    name='idiomssolitaire',
    help='A high-performance Chinese idioms solitaire tool',
    add_completion=False,
)


@app.command()
def main(
    idiom: str = typer.Argument(..., help='Input Chinese idiom'),
    db: str | None = typer.Option(
        None, '--db', '-d', help='Database file path',
    ),
) -> None:
    """Find a matching idiom for solitaire game."""
    try:
        # Initialize database
        init_db(db)

        # Find matching idiom
        result = guess(idiom)

        if result:
            word, meaning = result
            # Create beautiful output with Rich
            text = Text()
            text.append(word, style='bold cyan')
            text.append(' : ', style='dim')
            text.append(meaning, style='white')

            panel = Panel(
                text,
                title='[bold green]Matching Idiom[/bold green]',
                border_style='green',
                padding=(1, 2),
            )
            console.print(panel)
        else:
            console.print(
                f"[yellow]No matching idiom found for[/yellow] [bold]{idiom}[/bold]",
            )

    except KeyboardInterrupt:
        logger.info('Interrupted by user')
        console.print('\n[yellow]Interrupted by user[/yellow]')
        raise typer.Exit(code=1)
    except Exception as e:
        logger.exception('Unexpected error', error=str(e))
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


def _configure_logging() -> None:
    """Configure structlog for structured logging."""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt='iso'),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def cli() -> None:
    """CLI entry point for package installation."""
    _configure_logging()
    app()


if __name__ == '__main__':
    _configure_logging()
    app()
