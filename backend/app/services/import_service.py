import io

import pandas as pd
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums import ActivityAction
from app.models.test_case import TestCase
from app.repositories.test_case_repository import TestCaseRepository
from app.schemas.import_result import ImportError as ImportErrorItem
from app.schemas.import_result import ImportResult
from app.services.activity_service import ActivityService

# Logical field -> accepted header aliases (matched case-insensitively, trimmed).
FIELD_ALIASES: dict[str, list[str]] = {
    "case_id": ["case id", "caseid", "case_id"],
    "title": ["title", "test case title", "name"],
    "priority": ["priority"],
    "technology": ["technology", "tech"],
    "release_version": ["release_version", "release version"],
    "execution_type": ["execution_type", "execution type", "test case execution type"],
    "deployment_status": ["deployment_status", "deployment status", "automation_deployment_status"],
    "product_line": ["product_line", "product line"],
    "suite_id": ["suite_id", "suite id", "suiteid"],
    "section_id": ["section_id", "section id"],
    "sdk_type": ["sdk_type", "sdk type"],
    "product_type": ["product_type", "product type"],
    "test_case_status": ["test_case_status", "test case status", "deprecation_status"],
}

# Headers that must be present (mapped via aliases) for a valid import.
REQUIRED_FIELDS = ["case_id", "title"]

CHUNK_SIZE = 1000


class ImportService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = TestCaseRepository(db)
        self.activity = ActivityService(db)

    def _read_dataframe(self, filename: str, content: bytes) -> pd.DataFrame:
        name = filename.lower()
        try:
            if name.endswith(".csv"):
                return pd.read_csv(io.BytesIO(content), dtype=str, keep_default_na=False)
            if name.endswith(".xlsx"):
                return self._read_best_sheet(content)
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Failed to parse file: {exc}"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Only .csv and .xlsx are allowed.",
        )

    def _read_best_sheet(self, content: bytes) -> pd.DataFrame:
        """Pick the sheet that contains the required columns (case_id + title)."""
        xls = pd.ExcelFile(io.BytesIO(content), engine="openpyxl")
        best: pd.DataFrame | None = None
        for sheet in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet, dtype=str).fillna("")
            if df.empty:
                continue
            resolved = self._resolve_columns([str(c).strip() for c in df.columns])
            if all(field in resolved for field in REQUIRED_FIELDS):
                return df
            if best is None:
                best = df
        if best is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No worksheet with the required columns (Case ID, Title) was found.",
            )
        return best

    def _resolve_columns(self, headers: list[str]) -> dict[str, str]:
        """Map logical field name -> actual header present in the file."""
        normalized = {h.strip().lower(): h for h in headers}
        resolved: dict[str, str] = {}
        for field, aliases in FIELD_ALIASES.items():
            for alias in aliases:
                if alias in normalized:
                    resolved[field] = normalized[alias]
                    break
        return resolved

    def import_file(self, filename: str, content: bytes, user_id: int) -> ImportResult:
        df = self._read_dataframe(filename, content)
        df.columns = [str(c).strip() for c in df.columns]
        resolved = self._resolve_columns(list(df.columns))

        missing = [f for f in REQUIRED_FIELDS if f not in resolved]
        if missing:
            pretty = {"case_id": "Case ID", "title": "Title"}
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Missing required columns: {', '.join(pretty.get(m, m) for m in missing)}",
            )

        errors: list[ImportErrorItem] = []
        seen_in_file: set[str] = set()
        candidate_case_ids: list[str] = []
        rows: list[dict] = []

        case_col = resolved["case_id"]
        title_col = resolved["title"]

        for idx, row in df.iterrows():
            row_num = int(idx) + 2  # +2 accounts for header row and 0-based index
            case_id = str(row.get(case_col, "")).strip()
            title = str(row.get(title_col, "")).strip()
            if not case_id:
                errors.append(ImportErrorItem(row=row_num, case_id=None, reason="Missing Case ID"))
                continue
            if not title:
                errors.append(ImportErrorItem(row=row_num, case_id=case_id, reason="Missing Title"))
                continue
            if case_id in seen_in_file:
                errors.append(ImportErrorItem(row=row_num, case_id=case_id, reason="Duplicate Case ID in file"))
                continue
            seen_in_file.add(case_id)
            candidate_case_ids.append(case_id)
            rows.append({"row_num": row_num, "data": row})

        existing = set()
        for i in range(0, len(candidate_case_ids), 5000):
            existing |= self.repo.existing_case_ids(candidate_case_ids[i : i + 5000])

        to_insert: list[TestCase] = []
        skipped_duplicates = 0
        for item in rows:
            row = item["data"]
            case_id = str(row.get(case_col, "")).strip()
            if case_id in existing:
                skipped_duplicates += 1
                errors.append(
                    ImportErrorItem(row=item["row_num"], case_id=case_id, reason="Duplicate Case ID (already exists)")
                )
                continue
            payload: dict[str, str | None] = {}
            for field, header in resolved.items():
                value = str(row.get(header, "")).strip()
                payload[field] = value or None
            payload["case_id"] = case_id
            payload["title"] = str(row.get(title_col, "")).strip()
            to_insert.append(TestCase(**payload))

        for i in range(0, len(to_insert), CHUNK_SIZE):
            self.repo.bulk_insert(to_insert[i : i + CHUNK_SIZE])

        result = ImportResult(
            total_rows=int(len(df)),
            imported=len(to_insert),
            skipped_duplicates=skipped_duplicates,
            failed=len(errors) - skipped_duplicates,
            errors=errors[:200],
        )
        self.activity.log(
            user_id=user_id, action=ActivityAction.IMPORT, entity_type="test_case",
            details=f"file={filename} imported={result.imported} skipped={skipped_duplicates} failed={result.failed}",
        )
        self.db.commit()
        return result
