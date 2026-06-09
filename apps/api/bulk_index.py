"""
StudyABHI — Bulk PDF Indexer
Uploads all PDFs from study-materials/ into the RAG pipeline.

Usage:
    cd apps/api
    python bulk_index.py

Make sure the FastAPI server is running first:
    uvicorn app.main:app --reload --port 8000
"""

import os
import sys
import time
import json
import asyncio
import mimetypes
from pathlib import Path

import httpx

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# ── Config ────────────────────────────────────────────────────────────────────
BASE_URL        = "http://127.0.0.1:8000/api/v1"
STUDY_MATERIALS = Path(__file__).parent.parent.parent / "study-materials"

# Credentials — change if different
EMAIL    = "abhitha@gmail.com"
PASSWORD = "Abhitha@123"

# Rate-limiting: wait this many seconds between uploads to avoid overloading
# the NVIDIA NIM embedding endpoint
DELAY_BETWEEN_UPLOADS = 3   # seconds
MAX_RETRIES           = 2

# Subject → human-readable description map
SUBJECT_DESCRIPTIONS = {
    "Art-Culture":             "Indian Art & Culture — UPSC GS Paper I",
    "Current-Affairs":         "Current Affairs — Monthly compilations for UPSC Prelims & Mains",
    "Economy":                 "Indian Economy — UPSC GS Paper III",
    "Environment":             "Environment & Ecology — UPSC GS Paper III",
    "Geography":               "Indian & World Geography — UPSC GS Paper I",
    "History":                 "Indian History — UPSC GS Paper I",
    "International-Relations": "International Relations — UPSC GS Paper II",
    "NCERT-Class-6-9":         "NCERT Foundation — Classes 6–9 for UPSC Base Preparation",
    "Polity":                  "Indian Polity & Governance — UPSC GS Paper II",
    "Science-Technology":      "Science & Technology — UPSC GS Paper III",
    "Social-Issues":           "Social Issues — UPSC GS Paper II & Essay",
    "Sociology":               "Sociology — UPSC Optional Subject",
}

# ANSI colours
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


# ── Helpers ───────────────────────────────────────────────────────────────────

def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


def bar(done: int, total: int, width: int = 30) -> str:
    filled = int(width * done / total) if total else 0
    return f"[{'█' * filled}{'░' * (width - filled)}]"


# ── Auth ──────────────────────────────────────────────────────────────────────

def get_token(client: httpx.Client) -> str:
    """Authenticate and return Bearer token."""
    print(f"\n{CYAN}🔐  Authenticating as {EMAIL}...{RESET}")
    resp = client.post(
        f"{BASE_URL}/auth/login",
        json={"email": EMAIL, "password": PASSWORD},
        timeout=15,
    )
    if resp.status_code != 200:
        print(f"{RED}✗  Login failed ({resp.status_code}): {resp.text}{RESET}")
        sys.exit(1)

    data = resp.json()
    token = data.get("tokens", {}).get("access_token")
    if not token:
        print(f"{RED}✗  No access_token in response: {data}{RESET}")
        sys.exit(1)

    print(f"{GREEN}✓  Authenticated successfully{RESET}")
    return token


# ── Already-uploaded check ─────────────────────────────────────────────────

def get_existing_filenames(client: httpx.Client, headers: dict) -> set[str]:
    """Fetch list of already-uploaded documents to skip duplicates."""
    existing = set()
    page = 1
    while True:
        resp = client.get(
            f"{BASE_URL}/documents",
            params={"page": page, "limit": 100},
            headers=headers,
            timeout=15,
        )
        if resp.status_code != 200:
            break
        data = resp.json()
        items = data.get("items", [])
        for item in items:
            existing.add(item.get("original_filename", ""))
        if page >= data.get("pages", 1):
            break
        page += 1

    return existing


# ── Upload ────────────────────────────────────────────────────────────────────

def upload_pdf(
    client: httpx.Client,
    headers: dict,
    pdf_path: Path,
    title: str,
    description: str,
) -> dict:
    """Upload a single PDF. Returns result dict."""
    with open(pdf_path, "rb") as f:
        content = f.read()

    for attempt in range(1, MAX_RETRIES + 2):
        try:
            resp = client.post(
                f"{BASE_URL}/documents/upload",
                files={"file": (pdf_path.name, content, "application/pdf")},
                data={
                    "title": title,
                    "description": description,
                    "auto_process": "true",
                },
                headers=headers,
                timeout=120,   # PDF processing can take a while
            )
            if resp.status_code in (200, 201):
                return {"ok": True, "data": resp.json()}
            elif resp.status_code == 400 and "duplicate" in resp.text.lower():
                return {"ok": True, "skipped": True, "reason": "duplicate"}
            else:
                if attempt <= MAX_RETRIES:
                    time.sleep(2 * attempt)
                    continue
                return {"ok": False, "status": resp.status_code, "error": resp.text[:200]}
        except httpx.TimeoutException:
            if attempt <= MAX_RETRIES:
                time.sleep(5)
                continue
            return {"ok": False, "error": "Request timed out after retries"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    return {"ok": False, "error": "Max retries exceeded"}


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}  StudyABHI — Bulk PDF Indexer{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}")

    if not STUDY_MATERIALS.exists():
        print(f"{RED}✗  study-materials/ not found at: {STUDY_MATERIALS}{RESET}")
        sys.exit(1)

    # Collect all PDFs
    all_pdfs: list[tuple[Path, str]] = []   # (path, subject_folder_name)
    for subject_dir in sorted(STUDY_MATERIALS.iterdir()):
        if not subject_dir.is_dir():
            continue
        for pdf in sorted(subject_dir.glob("*.pdf")):
            all_pdfs.append((pdf, subject_dir.name))

    total = len(all_pdfs)
    if total == 0:
        print(f"{YELLOW}⚠  No PDFs found in {STUDY_MATERIALS}{RESET}")
        sys.exit(0)

    total_size = sum(p.stat().st_size for p, _ in all_pdfs)
    print(f"\n{CYAN}Found {BOLD}{total} PDFs{RESET}{CYAN} across {len(SUBJECT_DESCRIPTIONS)} subjects ({human_size(total_size)} total){RESET}")

    # Show subject breakdown
    from collections import Counter
    subject_counts = Counter(s for _, s in all_pdfs)
    for subj, cnt in sorted(subject_counts.items()):
        print(f"  {YELLOW}•{RESET} {subj:<30} {cnt} PDF(s)")

    print(f"\n{YELLOW}⚡  Starting upload. Server must be running on port 8000.{RESET}")
    print(f"{YELLOW}   Delay between uploads: {DELAY_BETWEEN_UPLOADS}s (to protect embedding rate limits){RESET}\n")

    with httpx.Client() as client:
        token = get_token(client)
        auth_headers = {"Authorization": f"Bearer {token}"}

        # Check already-uploaded to allow resuming
        print(f"{CYAN}📋  Checking existing documents (safe to re-run)...{RESET}")
        existing = get_existing_filenames(client, auth_headers)
        print(f"    {len(existing)} document(s) already indexed — will skip duplicates.\n")

        # ── Upload loop ──
        succeeded  = []
        failed     = []
        skipped    = []

        for i, (pdf_path, subject) in enumerate(all_pdfs, 1):
            prefix = f"[{i:02d}/{total}]"
            progress_bar = bar(i - 1, total)

            # Skip if already uploaded
            if pdf_path.name in existing:
                print(f"{progress_bar} {prefix} {YELLOW}SKIP{RESET}  {pdf_path.name[:55]}")
                skipped.append(pdf_path.name)
                continue

            size_str   = human_size(pdf_path.stat().st_size)
            title      = pdf_path.stem.replace("-", " ").replace("_", " ")
            description = SUBJECT_DESCRIPTIONS.get(subject, subject)

            print(f"{progress_bar} {prefix} {CYAN}↑{RESET}  {pdf_path.name[:50]:50s}  ({size_str})", end="", flush=True)

            result = upload_pdf(client, auth_headers, pdf_path, title, description)

            if result.get("ok"):
                if result.get("skipped"):
                    print(f"\r{progress_bar} {prefix} {YELLOW}SKIP{RESET}  {pdf_path.name[:55]}")
                    skipped.append(pdf_path.name)
                else:
                    doc_id = result["data"].get("id", "?")
                    print(f"\r{progress_bar} {prefix} {GREEN}✓ OK{RESET}  {pdf_path.name[:50]:50s}  id={doc_id[:8]}…")
                    succeeded.append({"file": pdf_path.name, "id": doc_id, "subject": subject})
            else:
                err = result.get("error", "unknown")
                print(f"\r{progress_bar} {prefix} {RED}✗ ERR{RESET} {pdf_path.name[:50]:50s}  {err[:60]}")
                failed.append({"file": pdf_path.name, "subject": subject, "error": err})

            # Rate-limit delay (skip for last file)
            if i < total:
                time.sleep(DELAY_BETWEEN_UPLOADS)

        # ── Summary ──
        print(f"\n{BOLD}{'=' * 60}{RESET}")
        print(f"{BOLD}  Indexing Complete{RESET}")
        print(f"{BOLD}{'=' * 60}{RESET}")
        print(f"  {GREEN}✓ Uploaded : {len(succeeded)}{RESET}")
        print(f"  {YELLOW}↷ Skipped  : {len(skipped)}  (already indexed){RESET}")
        print(f"  {RED}✗ Failed   : {len(failed)}{RESET}")

        if failed:
            print(f"\n{RED}Failed files:{RESET}")
            for f in failed:
                print(f"  • [{f['subject']}] {f['file']}")
                print(f"    Error: {f['error']}")

        # Save report
        report = {
            "timestamp"  : time.strftime("%Y-%m-%dT%H:%M:%S"),
            "total_pdfs" : total,
            "succeeded"  : succeeded,
            "skipped"    : skipped,
            "failed"     : failed,
        }
        report_path = Path(__file__).parent / "bulk_index_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n{CYAN}📄  Full report saved to: {report_path.name}{RESET}")

        if failed:
            print(f"\n{YELLOW}Tip: Re-run this script anytime — it skips already-indexed files.{RESET}")
            sys.exit(1)
        else:
            print(f"\n{GREEN}{BOLD}All PDFs are now indexed. The RAG pipeline is live! ✓{RESET}")


if __name__ == "__main__":
    main()
