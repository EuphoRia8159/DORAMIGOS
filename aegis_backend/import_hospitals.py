"""AEGIS Excel Hospital Dataset Importer.

Imports and synchronizes hospital records from Excel (sweekar_hospital_cleaned-1.xlsx)
into the AEGIS database with idempotency, data validation, coordinate normalization,
and clinical capability parsing.
"""

import argparse
import json
import logging
import math
import os
import re
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy.orm import Session

from aegis_backend.database import SessionLocal, init_db
from aegis_backend.models import Hospital

logger = logging.getLogger("aegis.importer")


def clean_text(val: Any) -> Optional[str]:
    """Cleans text values, handling zeroes, floats, and empty representations."""
    if pd.isna(val) or val is None:
        return None
    val_str = str(val).strip()
    if val_str.lower() in ("", "0", "0.0", "nan", "none", "null"):
        return None
    if val_str.endswith(".0") and val_str[:-2].isdigit():
        val_str = val_str[:-2]
    return val_str


def parse_coordinates(coord_val: Any) -> Tuple[Optional[float], Optional[float]]:
    """Validates and parses latitude and longitude from coordinate string."""
    text = clean_text(coord_val)
    if not text:
        return None, None

    # Handle comma-separated coords: 'lat, lon' or 'lat,lon'
    parts = text.split(",")
    if len(parts) != 2:
        return None, None

    try:
        lat = float(parts[0].strip())
        lon = float(parts[1].strip())
        # Validate geographic bounds and reject (0.0, 0.0)
        if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0 and not (lat == 0.0 and lon == 0.0):
            return round(lat, 6), round(lon, 6)
    except (ValueError, TypeError):
        pass

    return None, None


def parse_list_field(val: Any) -> List[str]:
    """Splits comma, semicolon, or newline delimited strings into clean unique list."""
    text = clean_text(val)
    if not text:
        return []

    # Replace newlines with commas, split on commas and semicolons
    normalized = re.sub(r"[\r\n]+", ",", text)
    items = [item.strip() for item in re.split(r"[,;]+", normalized) if item.strip()]

    # Deduplicate while preserving order
    seen = set()
    result = []
    for item in items:
        # Strip bullet points and punctuation
        cleaned = re.sub(r"^[\s\-\*\.\d]+\s*", "", item).strip()
        if cleaned and cleaned.lower() not in seen and cleaned.lower() not in ("0", "none", "na"):
            seen.add(cleaned.lower())
            result.append(cleaned)
    return result


def extract_capabilities(
    specialties: List[str],
    facilities: List[str],
    care_type: Optional[str] = None
) -> Dict[str, Any]:
    """Extracts diagnostic and specialty capabilities strictly supported by source data."""
    corpus = " ".join(specialties + facilities + ([care_type] if care_type else [])).lower()

    has_cath_lab = bool(
        "cath lab" in corpus
        or "interventional cardiology" in corpus
        or "cardiac cath" in corpus
    )
    has_stroke_center = bool(
        "stroke" in corpus
        or "interventional neuroradiology" in corpus
        or "neuro icu" in corpus
    )
    has_ct_scanner = bool(
        "ct scan" in corpus
        or "computed tomography" in corpus
        or "radio-diagnosis" in corpus
        or "radiology" in corpus
    )
    has_mri = bool(
        "mri" in corpus
        or "magnetic resonance" in corpus
    )
    has_burn_unit = bool(
        "burn" in corpus
    )
    has_pediatric_icu = bool(
        "picu" in corpus
        or "pediatric icu" in corpus
        or "pediatric intensive" in corpus
        or "neonatal intensive" in corpus
        or "nicu" in corpus
    )
    has_hyperbaric_chamber = bool(
        "hyperbaric" in corpus
    )

    # Trauma certification from source evidence
    if "trauma" in corpus and ("level 1" in corpus or "comprehensive" in corpus):
        trauma_level = "Level 1"
    elif "trauma" in corpus:
        trauma_level = "Level 2"
    elif care_type and "hospital" in care_type.lower():
        trauma_level = "Community"
    else:
        trauma_level = "General Care"

    return {
        "has_cath_lab": has_cath_lab,
        "has_stroke_center": has_stroke_center,
        "has_ct_scanner": has_ct_scanner,
        "has_mri": has_mri,
        "has_burn_unit": has_burn_unit,
        "has_pediatric_icu": has_pediatric_icu,
        "has_hyperbaric_chamber": has_hyperbaric_chamber,
        "trauma_level": trauma_level
    }


def compile_address(row: pd.Series) -> str:
    """Builds a human-readable complete address from available location parts."""
    parts = []
    line1 = clean_text(row.get("address_original_first_line"))
    location = clean_text(row.get("location"))
    subdistrict = clean_text(row.get("subdistrict"))
    district = clean_text(row.get("district"))
    state = clean_text(row.get("state"))
    pincode = clean_text(row.get("pincode"))

    if line1:
        parts.append(line1)
    if location and location != line1:
        parts.append(location)
    if subdistrict and subdistrict not in parts:
        parts.append(subdistrict)
    if district and district not in parts:
        parts.append(district)
    if state and state not in parts:
        parts.append(state)
    if pincode:
        parts.append(f"PIN: {pincode}")

    if not parts:
        return "Address Unspecified"
    return ", ".join(parts)[:495]


def extract_contact_phone(row: pd.Series) -> str:
    """Extracts the first valid contact phone number without fabricating data."""
    for col in ("emergency_num", "mobile_number", "telephone", "ambulance_phone_no", "tollfree", "helpline"):
        phone = clean_text(row.get(col))
        if phone:
            return phone[:95]
    return "Not Provided"


class HospitalImporter:
    """Idempotent batch importer for hospital dataset."""

    def __init__(self, db: Session, batch_size: int = 500):
        self.db = db
        self.batch_size = batch_size

    def import_from_excel(
        self,
        file_path: str,
        sheet_name: str = "in",
        limit: Optional[int] = None,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """Reads Excel workbook and imports/updates hospital records idempotently."""
        start_time = time.time()
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Workbook not found at: {file_path}")

        if verbose:
            logger.info("Reading Excel workbook: %s (Sheet: %s)...", file_path, sheet_name)

        df = pd.read_excel(file_path, sheet_name=sheet_name)
        if limit is not None and limit > 0:
            df = df.head(limit)

        total_source = len(df)
        inserted_count = 0
        updated_count = 0
        skipped_count = 0
        rejected_count = 0
        valid_coords_count = 0
        missing_coords_count = 0

        # Load existing hospital records index by unique code in memory for fast lookup
        existing_hospitals: Dict[str, Hospital] = {
            h.code: h for h in self.db.query(Hospital).all()
        }

        records_to_add: List[Hospital] = []

        for idx, row in df.iterrows():
            sr_no_val = row.get("sr_no")
            raw_name = clean_text(row.get("hospital_name"))

            if pd.isna(sr_no_val) or not raw_name:
                rejected_count += 1
                continue

            try:
                sr_no = int(float(str(sr_no_val).strip()))
            except (ValueError, TypeError):
                rejected_count += 1
                continue

            code = f"IN-HOSP-{sr_no}"
            hospital_name = raw_name[:195]
            address = compile_address(row)
            lat, lon = parse_coordinates(row.get("location_coordinates"))
            if lat is not None and lon is not None:
                valid_coords_count += 1
            else:
                missing_coords_count += 1

            contact_phone = extract_contact_phone(row)
            state = clean_text(row.get("state"))
            district = clean_text(row.get("district"))
            pincode = clean_text(row.get("pincode"))
            specialties = parse_list_field(row.get("specialties"))
            facilities = parse_list_field(row.get("facilities"))
            care_type = clean_text(row.get("hospital_care_type"))

            caps = extract_capabilities(specialties, facilities, care_type)

            # Bed metrics: Only record total beds if explicitly present in source data
            raw_beds = clean_text(row.get("total_num_beds"))
            total_beds = 0
            if raw_beds:
                try:
                    parsed_beds = int(float(raw_beds))
                    if parsed_beds > 0:
                        total_beds = parsed_beds
                except (ValueError, TypeError):
                    total_beds = 0

            # Directory data defaults:
            # We NEVER invent live bed availability, ICU units, ER surge load, or live integration
            available_beds = 0
            icu_total = 0
            icu_available = 0
            er_capacity = 0
            er_current_load = 0
            status = "DIRECTORY"
            data_source = "EXCEL_DIRECTORY"
            is_live_monitored = False
            ibm_z_connected = False

            existing = existing_hospitals.get(code)
            if existing:
                # Check if attributes differ to determine if update is needed
                has_changes = (
                    existing.name != hospital_name
                    or existing.address != address
                    or existing.latitude != lat
                    or existing.longitude != lon
                    or existing.contact_phone != contact_phone
                    or existing.state != state
                    or existing.district != district
                    or existing.pincode != pincode
                    or existing.total_beds != total_beds
                    or existing.specialties != specialties
                    or existing.facilities != facilities
                )
                if has_changes:
                    existing.name = hospital_name
                    existing.address = address
                    existing.latitude = lat
                    existing.longitude = lon
                    existing.contact_phone = contact_phone
                    existing.state = state
                    existing.district = district
                    existing.pincode = pincode
                    existing.total_beds = total_beds
                    existing.specialties = specialties
                    existing.facilities = facilities
                    existing.trauma_level = caps["trauma_level"]
                    existing.has_cath_lab = caps["has_cath_lab"]
                    existing.has_stroke_center = caps["has_stroke_center"]
                    existing.has_ct_scanner = caps["has_ct_scanner"]
                    existing.has_mri = caps["has_mri"]
                    existing.has_burn_unit = caps["has_burn_unit"]
                    existing.has_pediatric_icu = caps["has_pediatric_icu"]
                    existing.has_hyperbaric_chamber = caps["has_hyperbaric_chamber"]
                    updated_count += 1
                else:
                    skipped_count += 1
            else:
                # Create new Hospital record
                new_hosp = Hospital(
                    name=hospital_name,
                    code=code,
                    address=address,
                    latitude=lat,
                    longitude=lon,
                    contact_phone=contact_phone,
                    trauma_level=caps["trauma_level"],
                    state=state,
                    district=district,
                    pincode=pincode,
                    total_beds=total_beds,
                    available_beds=available_beds,
                    icu_total=icu_total,
                    icu_available=icu_available,
                    er_capacity=er_capacity,
                    er_current_load=er_current_load,
                    has_cath_lab=caps["has_cath_lab"],
                    has_stroke_center=caps["has_stroke_center"],
                    has_ct_scanner=caps["has_ct_scanner"],
                    has_mri=caps["has_mri"],
                    has_burn_unit=caps["has_burn_unit"],
                    has_pediatric_icu=caps["has_pediatric_icu"],
                    has_hyperbaric_chamber=caps["has_hyperbaric_chamber"],
                    status=status,
                    data_source=data_source,
                    is_live_monitored=is_live_monitored,
                    ibm_z_connected=ibm_z_connected
                )
                new_hosp.specialties = specialties
                new_hosp.facilities = facilities
                records_to_add.append(new_hosp)
                existing_hospitals[code] = new_hosp
                inserted_count += 1

            # Commit in batches for transactional safety and memory performance
            if len(records_to_add) >= self.batch_size:
                try:
                    self.db.add_all(records_to_add)
                    self.db.commit()
                    records_to_add.clear()
                except Exception as e:
                    self.db.rollback()
                    logger.error("Error committing batch: %s", e)
                    raise

        # Commit remaining records
        if records_to_add:
            try:
                self.db.add_all(records_to_add)
                self.db.commit()
                records_to_add.clear()
            except Exception as e:
                self.db.rollback()
                logger.error("Error committing final batch: %s", e)
                raise
        elif updated_count > 0:
            self.db.commit()

        elapsed_sec = round(time.time() - start_time, 2)

        report = {
            "total_source_records": total_source,
            "successfully_inserted_records": inserted_count,
            "updated_records": updated_count,
            "skipped_records": skipped_count,
            "rejected_records": rejected_count,
            "valid_coordinates": valid_coords_count,
            "missing_coordinates": missing_coords_count,
            "elapsed_seconds": elapsed_sec
        }

        if verbose:
            print("\n" + "=" * 60)
            print(" AEGIS HOSPITAL DATASET IMPORT REPORT ")
            print("=" * 60)
            print(f" Total Source Records:            {total_source}")
            print(f" Successfully Inserted Records:   {inserted_count}")
            print(f" Updated Records:                 {updated_count}")
            print(f" Skipped Records (Unchanged):     {skipped_count}")
            print(f" Rejected Records:                {rejected_count}")
            print(f" Records with Valid Coordinates:  {valid_coords_count}")
            print(f" Records Missing Coordinates:     {missing_coords_count}")
            print(f" Processing Time:                 {elapsed_sec} seconds")
            print("=" * 60 + "\n")

        return report


def import_hospitals(
    file_path: str = "sweekar_hospital_cleaned-1.xlsx",
    sheet_name: str = "in",
    batch_size: int = 500,
    limit: Optional[int] = None,
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """Public helper function to run hospital dataset import."""
    init_db()
    owns_session = False
    if db is None:
        db = SessionLocal()
        owns_session = True

    try:
        importer = HospitalImporter(db=db, batch_size=batch_size)
        return importer.import_from_excel(file_path=file_path, sheet_name=sheet_name, limit=limit)
    finally:
        if owns_session:
            db.close()


def main():
    """Command-line entrypoint for hospital import."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description="AEGIS Excel Hospital Dataset Importer")
    parser.add_argument("--file", "-f", default="sweekar_hospital_cleaned-1.xlsx", help="Path to Excel dataset file")
    parser.add_argument("--sheet", "-s", default="in", help="Excel sheet name (default: in)")
    parser.add_argument("--batch-size", "-b", type=int, default=500, help="Batch commit size (default: 500)")
    parser.add_argument("--limit", "-l", type=int, default=None, help="Limit number of records to import (for testing)")
    args = parser.parse_args()

    import_hospitals(
        file_path=args.file,
        sheet_name=args.sheet,
        batch_size=args.batch_size,
        limit=args.limit
    )


if __name__ == "__main__":
    main()
