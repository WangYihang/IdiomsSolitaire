#!/usr/bin/env python
"""
IdiomsSolitaire - Chinese Idioms Solitaire Tool

A high-performance Chinese idioms solitaire program using SQLite database
for fast querying and random matching.
"""
import random
import time
from pathlib import Path

import structlog
import typer
from pypinyin import pinyin
from pypinyin import Style
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
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
    """Get all idioms that start with the last character of the given word.

    Results are sorted so that idioms starting with the same character (汉字匹配)
    come before those that only match by pinyin.
    """
    last_char = word[-1]
    last_pinyin = get_last_pinyin(word)
    logger.debug(
        'Searching idioms', last_char=last_char,
        last_pinyin=last_pinyin,
    )

    with Session(_engine) as session:
        statement = select(Idiom).where(Idiom.first_pinyin == last_pinyin)
        idioms = session.exec(statement).all()
        results = [(idiom.word, idiom.meaning) for idiom in idioms]

    # Sort: character match (汉字匹配) first, then pinyin-only match
    def sort_key(item: tuple[str, str]) -> tuple[int, str]:
        idiom_word = item[0]
        # 0 means character match (should come first), 1 means pinyin-only match
        match_type = 0 if idiom_word[0] == last_char else 1
        return (match_type, idiom_word)

    results.sort(key=sort_key)

    char_matches = sum(1 for w, _ in results if w[0] == last_char)
    logger.info(
        'Found matching idioms',
        count=len(results),
        char_matches=char_matches,
        pinyin_only_matches=len(results) - char_matches,
    )
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
    top: int | None = typer.Option(
        None, '--top', '-t', help='Number of results to return',
    ),
) -> None:
    """Find a matching idiom for solitaire game."""
    try:
        # Initialize database
        init_db(db)

        # Record start time
        start_time = time.time()

        # Get all matching idioms
        matches = get_all_starts_with(idiom)

        # Calculate elapsed time
        elapsed_time = time.time() - start_time

        if not matches:
            console.print(
                f"[yellow]No matching idiom found for[/yellow] [bold]{idiom}[/bold]",
            )
            console.print(
                f"[dim]Time elapsed: {elapsed_time * 1000:.2f}ms[/dim]",
            )
            return

        # Determine how many results to show
        if top is None:
            # Show single result, prefer character match (汉字匹配) if available
            char_matches = [m for m in matches if m[0][0] == idiom[-1]]
            if char_matches:
                result = random.choice(char_matches)
            else:
                result = random.choice(matches)
            word, meaning = result
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

            # Print statistics
            char_match_count = sum(1 for m in matches if m[0][0] == idiom[-1])
            stats_text = Text()
            stats_text.append(f'Total matches: {len(matches)}', style='dim')
            if char_match_count > 0:
                stats_text.append(
                    f' ({char_match_count} character matches)', style='dim',
                )
            stats_text.append(' | ', style='dim')
            stats_text.append(
                f'Time elapsed: {elapsed_time * 1000:.2f}ms', style='dim',
            )
            console.print(stats_text)
        else:
            # Show top N results, prioritizing character matches
            num_results = min(top, len(matches))
            # Select from sorted matches (character matches already come first)
            selected = matches[:num_results]

            table = Table(
                title=f'[bold green]Matching Idioms (Top {num_results})[/bold green]',
                border_style='green',
            )
            table.add_column('Idiom', style='bold cyan', width=20)
            table.add_column('Meaning', style='white')

            for word, meaning in selected:
                table.add_row(word, meaning)

            console.print(table)

            # Print statistics
            char_match_count = sum(1 for m in matches if m[0][0] == idiom[-1])
            stats_text = Text()
            stats_text.append(f'Total matches: {len(matches)}', style='dim')
            if char_match_count > 0:
                stats_text.append(
                    f' ({char_match_count} character matches)', style='dim',
                )
            stats_text.append(' | ', style='dim')
            stats_text.append(f'Returned: {num_results}', style='dim')
            stats_text.append(' | ', style='dim')
            stats_text.append(
                f'Time elapsed: {elapsed_time * 1000:.2f}ms', style='dim',
            )
            console.print(stats_text)

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
