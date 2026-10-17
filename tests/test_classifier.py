"""Unit tests for AEGIS AI Emergency Classification & Triage Engine."""

import pytest
from aegis_backend.classifier import EmergencyClassifier


def test_cardiac_arrest_classification():
    result = EmergencyClassifier.classify(
        chief_complaint="64-year-old male with sudden crushing chest pain radiating to jaw, diaphoresis, dyspnea",
        patient_age=64,
        patient_gender="M",
        vitals_bp="80/50",
        vitals_hr=135,
        vitals_spo2=89,
        vitals_gcs=14
    )
    assert result["category"] == "CARDIAC_ARREST"
    assert result["severity"] == "CRITICAL"
    assert result["needs_cath_lab"] is True
    assert "Cardiology" in result["required_specialties"]
    assert "CATH_LAB" in result["required_resources"]
    assert any("Hypotension" in flag for flag in result["risk_flags"])


def test_stroke_classification():
    result = EmergencyClassifier.classify(
        chief_complaint="Sudden right-sided facial droop and severe slurred speech, sudden arm weakness",
        patient_age=70,
        patient_gender="F",
        vitals_bp="185/105",
        vitals_hr=88,
        vitals_spo2=97,
        vitals_gcs=13
    )
    assert result["category"] == "ACUTE_STROKE"
    assert result["severity"] == "CRITICAL"
    assert result["needs_stroke_center"] is True
    assert "Neurology" in result["required_specialties"]
    assert "CT_SCANNER" in result["required_resources"]


def test_polytrauma_classification():
    result = EmergencyClassifier.classify(
        chief_complaint="High speed highway collision, passenger entrapped with multiple fractures and massive hemorrhage",
        patient_age=32,
        patient_gender="M",
        vitals_bp="75/40",
        vitals_hr=145,
        vitals_spo2=86,
        vitals_gcs=8
    )
    assert result["category"] == "POLYTRAUMA"
    assert result["severity"] == "CRITICAL"
    assert "Trauma Surgery" in result["required_specialties"]
    assert "TRAUMA_BAY" in result["required_resources"]
    assert any("Coma" in flag or "Neurological" in flag for flag in result["risk_flags"])


def test_pediatric_critical_classification():
    result = EmergencyClassifier.classify(
        chief_complaint="Toddler unresponsive with high fever and continuous seizure activity",
        patient_age=3,
        patient_gender="F",
        vitals_bp="90/60",
        vitals_hr=160,
        vitals_spo2=94,
        vitals_gcs=10
    )
    assert result["category"] == "PEDIATRIC_CRITICAL"
    assert "Pediatrics" in result["required_specialties"]
    assert "PEDIATRIC_ICU" in result["required_resources"]
