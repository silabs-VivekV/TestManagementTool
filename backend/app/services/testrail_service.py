from __future__ import annotations

import base64
import json
import os
import time

import pandas as pd
import requests
import urllib3
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.schemas.import_result import ImportResult
from app.services.import_service import ImportService

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Custom-field id -> label maps (ported from the psmr-tool's variables.py).
AUTOMATION_TYPE = {
    0: "Automatable", 1: "Automated", 2: "Manual", 3: "Automated_SDK_3.0",
    4: "Manual_SDK_3.0", 5: "Automated_Wearable_2.0", 6: "Manual_Wearable_2.0",
}
DEPLOYMENT_STATUS = {
    1: "Not Deployed", 2: "9116_NCP_Deployed", 3: "917_NCP_Deployed",
    4: "917_SoC_Deployed", 5: "WiFi_SDK_3.0_Deployed", 6: "917_Zephyr_Deployed",
}
# custom_deprecation_status -> "Test Case Status"
DEPRECATION_STATUS = {1: "Active", 2: "Draft", 3: "Test Case Removed", 4: "Test case Merged"}
PRODUCT_TYPE = {1: "RCP_OSD", 2: "RCP_Prop", 3: "NCP", 4: "SoC", 5: "FPGA"}
PRODUCT_LINE = {1: "9116", 2: "917", 3: "Everest", 4: "None"}
RELEASE_VERSION = {
    0: "Legacy", 1: "22Q4", 2: "23Q2", 3: "23Q4", 4: "22Q2", 5: "21Q4",
    6: "21Q2", 7: "24Q2", 8: "24Q4", 9: "25Q2", 10: "25Q4", 11: "26Q2",
}
TEST_SUITE_TYPE = {
    1: "ext_regression", 2: "Regression", 3: "Partial_Regression", 4: "Regression 2",
    5: "Alpha", 6: "ext_reg_alpha1", 7: "ext_reg_alpha2", 8: "ext_reg_alpha3", 9: "FPGA",
}
PRIORITY_ID = {1: "P3", 2: "P2", 3: "P1", 4: "P0"}
TECHNOLOGY = {
    1: "WLAN STA", 2: "WLAN AP", 3: "BTC", 4: "BLE", 5: "Concurrent STA + AP",
    6: "WLAN + BLE", 7: "WLAN + BT", 8: "WLAN + BT + BLE", 9: "WLAN + BT + ANT + BLE",
    10: "BLE IOP", 11: "HFP", 12: "HFP AG", 13: "ANT", 14: "BT+BLE", 15: "ANT+BT",
    16: "ANT + BT + BLE", 17: "Platform", 18: "BT Concurrency", 19: "HFP Concurrency",
    20: "WLAN Concurrency", 21: "WLAN",
}
SDK_TYPE = {1: "SAPI_2_0", 2: "WiFi_SDK_3_0"}

# Source column -> friendly header (must match ImportService aliases).
REQUIRED_COLUMNS = [
    "id", "title", "priority_id", "suite_id", "custom_automation_type",
    "custom_technology", "section_id", "custom_master_project_tc_id", "custom_sdk_type",
    "custom_deployment_status", "custom_product_line", "custom_test_suite_type",
    "custom_product_type", "custom_release_version", "custom_deprecation_status",
]
RENAMED_COLUMNS = {
    "id": "Case ID", "title": "Title", "priority_id": "Priority", "suite_id": "Suite ID",
    "section_id": "Section ID", "custom_automation_type": "Test Case Execution Type",
    "custom_technology": "Technology", "custom_master_project_tc_id": "Master Project TC Id",
    "custom_sdk_type": "SDK_Type", "custom_deployment_status": "Automation_Deployment_Status",
    "custom_product_line": "Product_line", "custom_test_suite_type": "Test Suite Type",
    "custom_product_type": "Product Type", "custom_release_version": "Release_Version",
    "custom_deprecation_status": "Test Case Status",
}


class _TestRailClient:
    """Minimal TestRail API v2 client (ported from the psmr-tool)."""

    def __init__(self, base_url: str, user: str, password: str):
        if not base_url.endswith("/"):
            base_url += "/"
        self._url = base_url + "index.php?/api/v2/"
        token = base64.b64encode(f"{user}:{password}".encode()).decode("ascii").strip()
        self._headers = {"Authorization": "Basic " + token, "Content-Type": "application/json"}

    def send_get(self, uri: str) -> dict:
        resp = requests.get(self._url + uri, headers=self._headers, verify=False, timeout=120)
        if resp.status_code > 201:
            try:
                detail = resp.json()
            except Exception:  # noqa: BLE001
                detail = resp.text
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"TestRail API returned HTTP {resp.status_code}: {detail}",
            )
        try:
            return resp.json()
        except Exception:  # noqa: BLE001
            return {}

    def get_all(self, uri: str, extract: str) -> list[dict]:
        """Follow pagination via _links.next, collecting `extract` items."""
        resp = self.send_get(uri)
        results: list[dict] = []
        while True:
            results.extend(resp.get(extract, []))
            nxt = resp.get("_links", {}).get("next") if isinstance(resp, dict) else None
            if not nxt:
                break
            resp = self.send_get(nxt.replace("/api/v2/", "").replace("&limit=250", ""))
            time.sleep(0.05)
        return results


class TestRailService:
    def __init__(self, db: Session):
        self.db = db

    def _client(self) -> _TestRailClient:
        if not settings.TESTRAIL_USER or not settings.TESTRAIL_PASSWORD:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="TestRail credentials are not configured. Set TESTRAIL_USER and "
                "TESTRAIL_PASSWORD in backend/.env.",
            )
        return _TestRailClient(settings.TESTRAIL_URL, settings.TESTRAIL_USER, settings.TESTRAIL_PASSWORD)

    def list_projects(self) -> list[dict]:
        client = self._client()
        info = client.send_get("get_projects")
        projects = info.get("projects", info if isinstance(info, list) else [])
        return [{"id": p.get("id"), "name": p.get("name")} for p in projects]

    @staticmethod
    def _map_value(value, mapping: dict):
        """Map a TestRail custom value (scalar or list of ids) to its label(s)."""
        if value is None:
            return None
        if isinstance(value, list):
            return str([mapping.get(item, item) for item in value])
        return mapping.get(value, value)

    def _map_cases_to_df(self, cases: list[dict], section_map: dict) -> pd.DataFrame:
        """Turn raw TestRail cases into the renamed/labelled Master Project List frame."""
        df = pd.DataFrame(cases)
        for col in REQUIRED_COLUMNS:
            if col not in df.columns:
                df[col] = None
        df = df[REQUIRED_COLUMNS]
        df.columns = [RENAMED_COLUMNS.get(c, c) for c in df.columns]

        mappings = [
            ("Automation_Deployment_Status", DEPLOYMENT_STATUS),
            ("SDK_Type", SDK_TYPE),
            ("Test Case Execution Type", AUTOMATION_TYPE),
            ("Product_line", PRODUCT_LINE),
            ("Test Suite Type", TEST_SUITE_TYPE),
            ("Product Type", PRODUCT_TYPE),
            ("Priority", PRIORITY_ID),
            ("Technology", TECHNOLOGY),
            ("Section ID", section_map),
            ("Release_Version", RELEASE_VERSION),
            ("Test Case Status", DEPRECATION_STATUS),
        ]
        for column, mapping in mappings:
            df[column] = df[column].apply(lambda v, m=mapping: self._map_value(v, m))
        return df

    def _build_dataframe(self, client: _TestRailClient, project_id: int, suite_id: int) -> pd.DataFrame:
        sections = client.get_all(f"get_sections/{project_id}&suite_id={suite_id}", "sections")
        section_map = {s.get("id"): s.get("name") for s in sections}
        cases = client.get_all(
            f"get_cases/{project_id}&suite_id={suite_id}{settings.TESTRAIL_CASES_PAYLOAD}", "cases"
        )
        if not cases:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No test cases found for Project {project_id} / Suite {suite_id}.",
            )
        return self._map_cases_to_df(cases, section_map)

    def _write_and_import(self, df: pd.DataFrame, user_id: int, db: Session) -> tuple[str, ImportResult]:
        output_path = settings.MASTER_LIST_OUTPUT
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
            df.to_excel(writer, sheet_name="Worksheet", index=False)
        with open(output_path, "rb") as fh:
            content = fh.read()
        result = ImportService(db).import_file(os.path.basename(output_path), content, user_id)
        return output_path, result

    def sync(self, project_id: int, suite_id: int, user_id: int) -> dict:
        """One-shot: fetch from TestRail -> write Master_Project_List.xlsx -> import into DB."""
        client = self._client()
        df = self._build_dataframe(client, project_id, suite_id)
        output_path, result = self._write_and_import(df, user_id, self.db)
        return {
            "project_id": project_id,
            "suite_id": suite_id,
            "fetched": int(len(df)),
            "output_file": output_path,
            "import_result": result,
        }

    def sync_stream(self, project_id: int, suite_id: int, user_id: int):
        """Generator yielding NDJSON progress lines while the sync runs.

        Uses its own DB session so it stays valid for the whole streamed response.
        """
        def emit(event_type: str, **kwargs) -> str:
            return json.dumps({"type": event_type, **kwargs}, default=str) + "\n"

        db = SessionLocal()
        try:
            client = self._client()
            yield emit("log", message=f"Connecting to TestRail ({settings.TESTRAIL_URL}) ...")
            yield emit("log", message=f"Fetching sections for Project {project_id} / Suite {suite_id} ...")
            sections = client.get_all(f"get_sections/{project_id}&suite_id={suite_id}", "sections")
            section_map = {s.get("id"): s.get("name") for s in sections}
            yield emit("log", message=f"Retrieved {len(sections)} sections.")

            yield emit("log", message="Fetching test cases (paginated) ...")
            cases: list[dict] = []
            uri = f"get_cases/{project_id}&suite_id={suite_id}{settings.TESTRAIL_CASES_PAYLOAD}"
            resp = client.send_get(uri)
            page = 0
            while True:
                cases.extend(resp.get("cases", []) if isinstance(resp, dict) else [])
                page += 1
                yield emit("log", message=f"  page {page} fetched - {len(cases)} cases so far")
                nxt = resp.get("_links", {}).get("next") if isinstance(resp, dict) else None
                if not nxt:
                    break
                resp = client.send_get(nxt.replace("/api/v2/", "").replace("&limit=250", ""))
                time.sleep(0.05)

            if not cases:
                yield emit("error", message=f"No test cases found for Project {project_id} / Suite {suite_id}.")
                return

            yield emit("log", message=f"Retrieved {len(cases)} cases. Mapping fields and building Master_Project_List.xlsx ...")
            df = self._map_cases_to_df(cases, section_map)

            output_path, result = self._write_and_import(df, user_id, db)
            yield emit("log", message=f"Saved {output_path}")
            yield emit("log", message="Importing into the database ...")
            yield emit(
                "log",
                message=(
                    f"Import complete - imported={result.imported}, "
                    f"skipped(duplicates)={result.skipped_duplicates}, failed={result.failed}"
                ),
            )
            yield emit(
                "result",
                data={
                    "project_id": project_id,
                    "suite_id": suite_id,
                    "fetched": int(len(df)),
                    "output_file": output_path,
                    "import_result": result.model_dump(),
                },
            )
            yield emit("log", message="Done. Dashboard will refresh automatically.")
        except HTTPException as exc:
            yield emit("error", message=str(exc.detail))
        except Exception as exc:  # noqa: BLE001
            yield emit("error", message=str(exc))
        finally:
            db.close()
