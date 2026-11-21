"""Streaming parser and validation for PubMed metadata NDJSON shards."""

import calendar
import gzip
import json
import re
from datetime import date
from pathlib import Path
from typing import Iterator


EXPECTED_RECORD_FIELDS = (
    "id",
    "journal_name",
    "journal_abbrev",
    "article_title",
    "volume",
    "issue",
    "pub_year",
    "pub_month",
    "pub_day",
    "abstract",
)
PMID_PATTERN = re.compile(r"^PMID:[1-9][0-9]*$")
YEAR_PATTERN = re.compile(r"^[0-9]{4}$")
NUMERIC_DATE_PART_PATTERN = re.compile(r"^[0-9]{1,2}$")
MONTH_NUMBERS = {
    month_abbreviation.lower(): month_number
    for month_number, month_abbreviation in enumerate(calendar.month_abbr)
    if month_abbreviation
}


class PubMedMetadataValidationError(ValueError):
    """Raised when an input shard or record does not match the contract."""


def _location(source: str, line_number: int | None) -> str:
    if line_number is None:
        return source
    return f"{source}:{line_number}"


def _parse_month(value: str, location: str) -> int:
    if NUMERIC_DATE_PART_PATTERN.fullmatch(value):
        month = int(value)
    else:
        month = MONTH_NUMBERS.get(value.lower(), 0)

    if not 1 <= month <= 12:
        raise PubMedMetadataValidationError(f"{location}: invalid publication month {value!r}")
    return month


def _build_pub_date(record: dict, location: str) -> str | None:
    year_value = record["pub_year"]
    month_value = record["pub_month"]
    day_value = record["pub_day"]

    if not year_value:
        if month_value or day_value:
            raise PubMedMetadataValidationError(f"{location}: publication month/day requires a year")
        return None

    if YEAR_PATTERN.fullmatch(year_value) is None or int(year_value) == 0:
        raise PubMedMetadataValidationError(f"{location}: invalid publication year {year_value!r}")

    if not month_value:
        if day_value:
            raise PubMedMetadataValidationError(f"{location}: publication day requires a month")
        return year_value

    month = _parse_month(month_value, location)
    year_month = f"{year_value}-{month:02d}"
    if not day_value:
        return year_month

    if NUMERIC_DATE_PART_PATTERN.fullmatch(day_value) is None:
        raise PubMedMetadataValidationError(f"{location}: invalid publication day {day_value!r}")

    day = int(day_value)
    try:
        publication_date = date(int(year_value), month, day)
    except ValueError as error:
        raise PubMedMetadataValidationError(
            f"{location}: invalid publication date {year_value!r}/{month_value!r}/{day_value!r}"
        ) from error
    return publication_date.isoformat()


def transform_pubmed_metadata_record(
    record: object,
    *,
    source: str = "<record>",
    line_number: int | None = None,
) -> dict:
    """Validate and namespace one upstream PubMed record."""
    location = _location(source, line_number)
    if not isinstance(record, dict):
        raise PubMedMetadataValidationError(
            f"{location}: expected a JSON object, got {type(record).__name__}"
        )

    expected_fields = set(EXPECTED_RECORD_FIELDS)
    actual_fields = set(record)
    missing_fields = sorted(expected_fields - actual_fields)
    extra_fields = sorted(str(field) for field in actual_fields - expected_fields)
    if missing_fields or extra_fields:
        details = []
        if missing_fields:
            details.append(f"missing fields: {', '.join(missing_fields)}")
        if extra_fields:
            details.append(f"unexpected fields: {', '.join(extra_fields)}")
        raise PubMedMetadataValidationError(f"{location}: {'; '.join(details)}")

    non_string_fields = sorted(
        field for field in EXPECTED_RECORD_FIELDS if not isinstance(record[field], str)
    )
    if non_string_fields:
        raise PubMedMetadataValidationError(
            f"{location}: fields must contain strings: {', '.join(non_string_fields)}"
        )

    pubmed_id = record["id"]
    if PMID_PATTERN.fullmatch(pubmed_id) is None:
        raise PubMedMetadataValidationError(f"{location}: invalid PubMed identifier {pubmed_id!r}")

    pubmed = {
        "journal": {
            "name": record["journal_name"],
            "abbr": record["journal_abbrev"],
        },
        "title": record["article_title"],
        "vol": record["volume"],
        "iss": record["issue"],
        "abstract": record["abstract"],
    }
    pub_date = _build_pub_date(record, location)
    if pub_date is not None:
        pubmed["pub_date"] = pub_date

    return {
        "_id": pubmed_id,
        "pubmed": pubmed,
    }


def iter_pubmed_metadata_documents(data_path: str | Path) -> Iterator[dict]:
    """Yield validated documents from a gzip-compressed NDJSON shard."""
    path = Path(data_path)
    try:
        with gzip.open(
            path,
            mode="rt",
            encoding="utf-8",
            errors="strict",
            newline="",
        ) as input_file:
            for line_number, line in enumerate(input_file, start=1):
                if not line.strip():
                    raise PubMedMetadataValidationError(
                        f"{path}:{line_number}: blank lines are not allowed"
                    )
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as error:
                    raise PubMedMetadataValidationError(
                        f"{path}:{line_number}: invalid JSON: {error.msg}"
                    ) from error

                yield transform_pubmed_metadata_record(
                    record,
                    source=str(path),
                    line_number=line_number,
                )
    except PubMedMetadataValidationError:
        raise
    except (EOFError, OSError, UnicodeError) as error:
        raise PubMedMetadataValidationError(f"{path}: unable to read gzip stream: {error}") from error
