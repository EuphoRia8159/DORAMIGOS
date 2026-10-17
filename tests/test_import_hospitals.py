"""Comprehensive Unit and Integration Tests for Hospital Dataset Importer.

Tests:
1. Import of valid hospital records
2. Missing values and field normalization (phone, pincode, address)
3. Invalid coordinates handling ("Error", out-of-range, (0,0))
4. Duplicate records and Idempotency on re-running
5. Empty datasets and safe handling
6. Database transaction rollback on errors
7. Clinical capability extraction from source evidence
"""

import os
import tempfile
import pytest
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from aegis_backend.database import Base
from aegis_backend.models import Hospital
from aegis_backend.import_hospitals import (
    HospitalImporter,
    clean_text,
    parse_coordinates,
    parse_list_field,
    extract_capabilities,
    compile_address,
    extract_contact_phone
)


@pytest.fixture
def memory_db():
    """In-memory SQLite database session with AEGIS schema."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    yield db
    db.close()


def test_clean_text_utility():
    assert clean_text(None) is None
    assert clean_text("") is None
    assert clean_text("0") is None
    assert clean_text(0) is None
    assert clean_text(0.0) is None
    assert clean_text("nan") is None
    assert clean_text("None") is None
    assert clean_text("744101.0") == "744101"
    assert clean_text("9876543210.0") == "9876543210"
    assert clean_text("  Apollo Hospital  ") == "Apollo Hospital"


def test_parse_coordinates_valid_and_invalid():
    # Valid coordinates
    lat, lon = parse_coordinates("11.6357989, 92.7120575")
    assert lat == 11.635799
    assert lon == 92.712058

    lat, lon = parse_coordinates(" 19.0760 , 72.8777 ")
    assert lat == 19.076
    assert lon == 72.8777

    # Non-numeric error strings (common in dataset)
    assert parse_coordinates("Error") == (None, None)
    assert parse_coordinates("0") == (None, None)
    assert parse_coordinates("0.0, 0.0") == (None, None)
    assert parse_coordinates(None) == (None, None)
    assert parse_coordinates("nan") == (None, None)

    # Out of range coordinates
    assert parse_coordinates("195.0, 45.0") == (None, None)
    assert parse_coordinates("45.0, 250.0") == (None, None)
    assert parse_coordinates("malformed,coord,extra") == (None, None)


def test_parse_list_field_and_capabilities():
    specs = parse_list_field("Cardiology, Critical Care\nNeurology, , Oncology; Trauma Surgery")
    assert "Cardiology" in specs
    assert "Critical Care" in specs
    assert "Neurology" in specs
    assert "Trauma Surgery" in specs

    caps = extract_capabilities(
        specialties=["Cardiology", "Interventional Cardiology", "Trauma Surgery"],
        facilities=["Cath Lab", "Blood Bank", "Pediatric ICU"],
        care_type="Multispeciality Hospital"
    )
    assert caps["has_cath_lab"] is True
    assert caps["has_pediatric_icu"] is True
    assert caps["has_burn_unit"] is False
    assert caps["has_hyperbaric_chamber"] is False
    assert caps["trauma_level"] in ("Level 1", "Level 2")


def test_compile_address_and_phone():
    row_data = {
        "address_original_first_line": "123 Medical Road",
        "location": "Near Clock Tower",
        "district": "Pune",
        "state": "Maharashtra",
        "pincode": "411001",
        "emergency_num": "0",
        "mobile_number": "9876543210",
        "telephone": "020-223344"
    }
    row = pd.Series(row_data)
    addr = compile_address(row)
    assert "123 Medical Road" in addr
    assert "Near Clock Tower" in addr
    assert "Pune" in addr
    assert "PIN: 411001" in addr

    phone = extract_contact_phone(row)
    # emergency_num was "0", mobile_number should be selected
    assert phone == "9876543210"


def test_import_hospitals_full_flow(memory_db):
    """Tests creating a workbook, importing records, checking DB values, and idempotency."""
    test_data = [
        {
            "sr_no": 101,
            "location_coordinates": "19.0760, 72.8777",
            "location": "Bandra West",
            "hospital_name": "City Care Trauma & Heart Institute",
            "hospital_category": "Private",
            "hospital_care_type": "Hospital",
            "discipline_systems_of_medicine": "Allopathic",
            "address_original_first_line": "Plot 45, Hill Road",
            "state": "Maharashtra",
            "district": "Mumbai",
            "subdistrict": "Bandra",
            "pincode": "400050",
            "telephone": "022-26400000",
            "mobile_number": "9820011223",
            "emergency_num": "022-26499999",
            "ambulance_phone_no": "108",
            "specialties": "Cardiology, Cardiothoracic Surgery, Interventional Cardiology, Trauma Surgery",
            "facilities": "Cath Lab, Emergency Room, Blood Bank, CT Scanner",
            "total_num_beds": 120
        },
        {
            "sr_no": 102,
            "location_coordinates": "Error",  # Invalid coordinates
            "location": "Camp Area",
            "hospital_name": "Deccan Community Clinic",
            "hospital_category": "Public/ Government",
            "hospital_care_type": "Dispensary",
            "discipline_systems_of_medicine": "Allopathic",
            "address_original_first_line": "MG Road",
            "state": "Maharashtra",
            "district": "Pune",
            "subdistrict": "Pune City",
            "pincode": "411001",
            "telephone": "020-26120000",
            "mobile_number": "0",
            "emergency_num": "0",
            "ambulance_phone_no": "0",
            "specialties": "0",
            "facilities": "0",
            "total_num_beds": 0
        },
        {
            "sr_no": 103,
            "location_coordinates": "0",  # Missing coordinates
            "location": "Civil Lines",
            "hospital_name": "",  # Missing name: should be rejected
            "hospital_category": "Private",
            "hospital_care_type": "Hospital",
            "discipline_systems_of_medicine": "Allopathic",
            "address_original_first_line": "Civil Lines",
            "state": "Uttar Pradesh",
            "district": "Kanpur",
            "subdistrict": "Kanpur",
            "pincode": "208001",
            "telephone": "0",
            "mobile_number": "0",
            "emergency_num": "0",
            "ambulance_phone_no": "0",
            "specialties": "0",
            "facilities": "0",
            "total_num_beds": 0
        }
    ]

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        df = pd.DataFrame(test_data)
        df.to_excel(tmp_path, sheet_name="in", index=False)

        importer = HospitalImporter(db=memory_db, batch_size=10)

        # 1. First import run
        report = importer.import_from_excel(tmp_path, sheet_name="in")
        assert report["total_source_records"] == 3
        assert report["successfully_inserted_records"] == 2
        assert report["updated_records"] == 0
        assert report["skipped_records"] == 0
        assert report["rejected_records"] == 1  # 103 rejected due to empty name
        assert report["valid_coordinates"] == 1
        assert report["missing_coordinates"] == 1

        # Verify DB records
        h1 = memory_db.query(Hospital).filter(Hospital.code == "IN-HOSP-101").first()
        assert h1 is not None
        assert h1.name == "City Care Trauma & Heart Institute"
        assert h1.latitude == 19.076
        assert h1.longitude == 72.8777
        assert h1.has_cath_lab is True
        assert h1.total_beds == 120
        # Verify directory constraints: live metrics must NOT be fabricated
        assert h1.available_beds == 0
        assert h1.icu_available == 0
        assert h1.er_current_load == 0
        assert h1.status == "DIRECTORY"
        assert h1.data_source == "EXCEL_DIRECTORY"
        assert h1.is_live_monitored is False

        h2 = memory_db.query(Hospital).filter(Hospital.code == "IN-HOSP-102").first()
        assert h2 is not None
        assert h2.latitude is None
        assert h2.longitude is None
        assert h2.total_beds == 0

        # 2. Second import run (Idempotency test)
        # Rerunning without changing the source must insert 0 and skip 2
        report2 = importer.import_from_excel(tmp_path, sheet_name="in")
        assert report2["total_source_records"] == 3
        assert report2["successfully_inserted_records"] == 0
        assert report2["updated_records"] == 0
        assert report2["skipped_records"] == 2
        assert report2["rejected_records"] == 1

        # 3. Update test: modify record 101 in workbook
        test_data[0]["emergency_num"] = "022-99999999"
        test_data[0]["hospital_name"] = "City Care Trauma & Heart Institute (Updated)"
        df_updated = pd.DataFrame(test_data)
        df_updated.to_excel(tmp_path, sheet_name="in", index=False)

        report3 = importer.import_from_excel(tmp_path, sheet_name="in")
        assert report3["successfully_inserted_records"] == 0
        assert report3["updated_records"] == 1
        assert report3["skipped_records"] == 1
        assert report3["rejected_records"] == 1

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_empty_dataset_handling(memory_db):
    """Tests importer resilience when given an empty workbook."""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        empty_df = pd.DataFrame(columns=["sr_no", "hospital_name", "location_coordinates"])
        empty_df.to_excel(tmp_path, sheet_name="in", index=False)

        importer = HospitalImporter(db=memory_db)
        report = importer.import_from_excel(tmp_path, sheet_name="in")
        assert report["total_source_records"] == 0
        assert report["successfully_inserted_records"] == 0
        assert report["updated_records"] == 0
        assert report["skipped_records"] == 0
        assert report["rejected_records"] == 0
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_database_transaction_error_handling(memory_db, monkeypatch):
    """Tests that DB transaction rolls back safely on failure."""
    test_data = [{
        "sr_no": 999,
        "hospital_name": "Test Rollback Hospital",
        "location_coordinates": "12.0, 77.0"
    }]
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        pd.DataFrame(test_data).to_excel(tmp_path, sheet_name="in", index=False)
        importer = HospitalImporter(db=memory_db, batch_size=1)

        # Force a database commit failure
        def mock_commit():
            raise RuntimeError("Simulated DB connection failure")

        monkeypatch.setattr(memory_db, "commit", mock_commit)

        with pytest.raises(RuntimeError, match="Simulated DB connection failure"):
            importer.import_from_excel(tmp_path, sheet_name="in")

        # Verify nothing was committed
        assert memory_db.query(Hospital).filter(Hospital.code == "IN-HOSP-999").first() is None
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
