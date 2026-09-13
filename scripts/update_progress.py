import re
import sys
from pathlib import Path


DOMAINS = ["Power BI", "SQL", "Coding"]

# Resolve paths relative to this script:
#
# repository/
# ├── README.md
# ├── scripts/
# │   └── update_progress.py
# └── weekly-reviews/
#     └── week-38.md

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent

WEEKLY_REVIEWS_DIR = ROOT_DIR / "weekly-reviews"
README_PATH = ROOT_DIR / "README.md"


def get_section(content: str, domain: str) -> str:
    """
    Extract the content belonging to a ## heading.

    Example:
        ## SQL
        ...
        ## Coding

    Returns everything between the specified heading
    and the next ## heading.
    """
    pattern = rf"^## {re.escape(domain)}\s*$\n(.*?)(?=^## |\Z)"

    match = re.search(
        pattern,
        content,
        flags=re.MULTILINE | re.DOTALL,
    )

    if not match:
        raise ValueError(f'Could not find section "## {domain}"')

    return match.group(1)


def calculate_progress(section: str) -> tuple[int, int, int]:
    """
    Count completed and total checkboxes.

    Supports:
        [x]
        [X]
        [ ]

    Returns:
        completed, total, percentage
    """
    checkboxes = re.findall(r"\[[ xX]\]", section)

    completed = sum(
        checkbox.lower() == "[x]"
        for checkbox in checkboxes
    )

    total = len(checkboxes)

    percentage = round((completed / total) * 100) if total else 0

    return completed, total, percentage


def update_target_row(
    content: str,
    domain: str,
    completed: int,
    total: int,
    percentage: int,
) -> str:
    """
    Update one row in the weekly Targets table.
    """
    new_row = (
        f"| {domain:<8} | "
        f'<progress value="{percentage}" max="100"></progress> '
        f"{completed}/{total} |"
    )

    pattern = rf"^\|\s*{re.escape(domain)}\s*\|.*\|$"

    updated_content, replacements = re.subn(
        pattern,
        new_row,
        content,
        count=1,
        flags=re.MULTILINE,
    )

    if replacements == 0:
        raise ValueError(
            f'Could not find "{domain}" in the Targets table'
        )

    return updated_content


def update_weekly_file(file_path: Path) -> dict[str, tuple[int, int]]:
    """
    Update the weekly Markdown file and return progress data.

    Example return value:
        {
            "Power BI": (2, 3),
            "SQL": (7, 9),
            "Coding": (1, 3)
        }
    """
    content = file_path.read_text(encoding="utf-8")

    progress = {}

    print("\nWeekly progress:")

    for domain in DOMAINS:
        section = get_section(content, domain)

        completed, total, percentage = calculate_progress(section)

        progress[domain] = (completed, total)

        content = update_target_row(
            content,
            domain,
            completed,
            total,
            percentage,
        )

        print(
            f"  {domain:<8}: "
            f"{completed}/{total} ({percentage}%)"
        )

    file_path.write_text(content, encoding="utf-8")

    return progress


def find_progress_table(content: str) -> re.Match:
    """
    Locate the table directly below the ## Progress heading.
    """
    pattern = (
        r"(^## Progress\s*\n+)"
        r"("
        r"\|[^\n]*\|\s*\n"
        r"\|[^\n]*\|\s*\n"
        r"(?:\|[^\n]*\|\s*\n?)*"
        r")"
    )

    match = re.search(
        pattern,
        content,
        flags=re.MULTILINE,
    )

    if not match:
        raise ValueError(
            'Could not find the table under "## Progress" in README.md'
        )

    return match


def create_week_row(
    week_number: int,
    progress: dict[str, tuple[int, int]],
) -> str:
    """
    Create a README Progress table row.
    """
    power_bi_completed, power_bi_total = progress["Power BI"]
    sql_completed, sql_total = progress["SQL"]
    coding_completed, coding_total = progress["Coding"]

    return (
        f"| {week_number:<9} | "
        f"{power_bi_completed}/{power_bi_total: <3} | "
        f"{sql_completed}/{sql_total: <3} | "
        f"{coding_completed}/{coding_total: <3} |"
    )


def is_total_row(line: str) -> bool:
    """
    Determine whether a README table row is the Total row.
    """
    return bool(
        re.match(
            r"^\|\s*\*{0,2}Total\*{0,2}\s*\|",
            line,
            flags=re.IGNORECASE,
        )
    )


def is_week_row(line: str) -> bool:
    """
    Determine whether a table row begins with a week number.
    """
    return bool(re.match(r"^\|\s*\d+\s*\|", line))


def get_week_number_from_row(line: str) -> int:
    """
    Extract the week number from a README progress row.
    """
    match = re.match(r"^\|\s*(\d+)\s*\|", line)

    if not match:
        raise ValueError(f"Invalid week row: {line}")

    return int(match.group(1))


def parse_week_progress(
    line: str,
) -> tuple[int, int, int]:
    """
    Extract completed counts from a README week row.

    Example:
        | 38 | 2/3 | 7/9 | 1/3 |

    Returns:
        (2, 7, 1)
    """
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]

    if len(cells) != 4:
        raise ValueError(
            f"Could not parse README progress row:\n{line}"
        )

    completed_values = []

    for value in cells[1:]:
        match = re.match(r"(\d+)\s*/\s*(\d+)", value)

        if not match:
            raise ValueError(
                f'Invalid progress value "{value}" in README.md'
            )

        completed_values.append(int(match.group(1)))

    return tuple(completed_values)


def create_total_row(week_rows: list[str]) -> str:
    """
    Calculate totals from every existing week row.
    """
    power_bi_total = 0
    sql_total = 0
    coding_total = 0

    for row in week_rows:
        power_bi, sql, coding = parse_week_progress(row)

        power_bi_total += power_bi
        sql_total += sql
        coding_total += coding

    return (
        f"| **Total** | "
        f"**{power_bi_total}** | "
        f"**{sql_total}** | "
        f"**{coding_total}** |"
    )


def update_readme(
    week_number: int,
    progress: dict[str, tuple[int, int]],
) -> None:
    """
    Update or insert the week's progress in README.md.

    Also recalculates the Total row.
    """
    if not README_PATH.exists():
        raise FileNotFoundError(
            f"Could not find README.md at: {README_PATH}"
        )

    content = README_PATH.read_text(encoding="utf-8")

    table_match = find_progress_table(content)

    table = table_match.group(2)

    lines = table.splitlines()

    if len(lines) < 2:
        raise ValueError("README Progress table is invalid.")

    header = lines[0]
    separator = lines[1]

    data_rows = lines[2:]

    new_week_row = create_week_row(
        week_number,
        progress,
    )

    week_rows = []
    week_found = False

    for line in data_rows:
        if is_total_row(line):
            continue

        if is_week_row(line):
            existing_week = get_week_number_from_row(line)

            if existing_week == week_number:
                week_rows.append(new_week_row)
                week_found = True
            else:
                week_rows.append(line)

    # If this week doesn't exist, add it.
    if not week_found:
        week_rows.append(new_week_row)

    # Keep the table ordered by week number.
    week_rows.sort(
        key=get_week_number_from_row
    )

    total_row = create_total_row(week_rows)

    new_table_lines = [
        header,
        separator,
        *week_rows,
        total_row,
    ]

    new_table = "\n".join(new_table_lines) + "\n"

    start, end = table_match.span(2)

    updated_content = (
        content[:start]
        + new_table
        + content[end:]
    )

    README_PATH.write_text(
        updated_content,
        encoding="utf-8",
    )

    print("\nREADME.md progress updated.")


def get_week_file() -> tuple[int, Path]:
    """
    Ask for a week number and return its Markdown file.

    Examples:
        1  -> weekly-reviews/week-01.md
        9  -> weekly-reviews/week-09.md
        38 -> weekly-reviews/week-38.md
    """
    week_input = input("Enter week number: ").strip()

    if not week_input.isdigit():
        raise ValueError(
            "Week number must be a positive integer."
        )

    week_number = int(week_input)

    if week_number <= 0:
        raise ValueError(
            "Week number must be greater than 0."
        )

    file_name = f"week-{week_number:02d}.md"

    file_path = WEEKLY_REVIEWS_DIR / file_name

    return week_number, file_path


def main() -> None:
    try:
        week_number, file_path = get_week_file()

        if not file_path.exists():
            raise FileNotFoundError(
                f"Could not find: {file_path}"
            )

        print(f"\nUpdating Week {week_number}")
        print(f"File: {file_path}")

        progress = update_weekly_file(file_path)

        update_readme(
            week_number,
            progress,
        )

        print("\nUpdated successfully.")

    except (
        ValueError,
        FileNotFoundError,
    ) as error:
        print(f"\nError: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()