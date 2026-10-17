"""AEGIS AI-Assisted Emergency Classification & Triage Engine.

Performs intelligent symptom parsing, vital sign risk stratification,
severity scoring, and medical specialty / resource mapping.
"""

from typing import Dict, List, Any, Optional
import re


CATEGORY_REQUIREMENTS = {
    "CARDIAC_ARREST": {
        "specialties": ["Cardiology", "Interventional Cardiology", "Cardiothoracic Surgery", "Critical Care"],
        "resources": ["CATH_LAB", "ICU_BED", "VENTILATOR"],
        "preferred_trauma": ["Level 1", "Level 2"],
        "needs_cath_lab": True,
        "needs_stroke_center": False,
    },
    "ACUTE_STROKE": {
        "specialties": ["Neurology", "Interventional Neuroradiology", "Neurosurgery", "Critical Care"],
        "resources": ["CT_SCANNER", "ICU_BED", "STROKE_UNIT"],
        "preferred_trauma": ["Level 1", "Level 2"],
        "needs_cath_lab": False,
        "needs_stroke_center": True,
    },
    "POLYTRAUMA": {
        "specialties": ["Trauma Surgery", "Orthopedics", "Neurosurgery", "Vascular Surgery", "Critical Care"],
        "resources": ["TRAUMA_BAY", "OPERATING_ROOM", "BLOOD_O_NEG", "CT_SCANNER", "ICU_BED"],
        "preferred_trauma": ["Level 1"],
        "needs_cath_lab": False,
        "needs_stroke_center": False,
    },
    "RESPIRATORY_FAILURE": {
        "specialties": ["Pulmonology", "Critical Care", "Internal Medicine"],
        "resources": ["VENTILATOR", "ICU_BED"],
        "preferred_trauma": ["Level 1", "Level 2", "Level 3"],
        "needs_cath_lab": False,
        "needs_stroke_center": False,
    },
    "SEVERE_BURN": {
        "specialties": ["Burn Care", "Plastic & Reconstructive Surgery", "Critical Care"],
        "resources": ["BURN_UNIT", "ICU_BED", "VENTILATOR"],
        "preferred_trauma": ["Level 1", "Level 2"],
        "needs_cath_lab": False,
        "needs_stroke_center": False,
    },
    "PEDIATRIC_CRITICAL": {
        "specialties": ["Pediatrics", "Pediatric Intensive Care", "Pediatric Surgery"],
        "resources": ["PEDIATRIC_ICU", "VENTILATOR"],
        "preferred_trauma": ["Level 1", "Level 2"],
        "needs_cath_lab": False,
        "needs_stroke_center": False,
    },
    "GENERAL_MEDICAL": {
        "specialties": ["Emergency Medicine", "Internal Medicine"],
        "resources": ["ICU_BED"],
        "preferred_trauma": ["Level 1", "Level 2", "Level 3", "Community"],
        "needs_cath_lab": False,
        "needs_stroke_center": False,
    }
}

KEYWORD_PATTERNS = {
    "CARDIAC_ARREST": [
        r"cardiac\s*arrest", r"heart\s*attack", r"chest\s*pain", r"stemi", r"ventricular\s*fibrillation",
        r"angina", r"myocardial\s*infarction", r"crushing\s*chest", r"asystole", r"no\s*pulse", r"defibrillat"
    ],
    "ACUTE_STROKE": [
        r"stroke", r"facial\s*droop", r"slurred\s*speech", r"hemiparesis", r"arm\s*weakness",
        r"aphasia", r"cerebral\s*infarct", r"sudden\s*numbness", r"cva", r"tia"
    ],
    "POLYTRAUMA": [
        r"polytrauma", r"mva", r"car\s*crash", r"motor\s*vehicle", r"pedestrian\s*struck",
        r"fall\s*from\s*height", r"gunshot", r"stab\s*wound", r"severe\s*bleeding", r"crush\s*injury",
        r"amputation", r"penetrating\s*trauma", r"multiple\s*fractures"
    ],
    "RESPIRATORY_FAILURE": [
        r"respiratory\s*arrest", r"can't\s*breathe", r"severe\s*dyspnea", r"choking",
        r"asthma\s*attack", r"cyanosis", r"stridor", r"suffocation", r"gasping", r"copd\s*exacerbation"
    ],
    "SEVERE_BURN": [
        r"burn", r"fire", r"explosion", r"chemical\s*burn", r"thermal\s*injury", r"scald", r"smoke\s*inhalation"
    ],
    "PEDIATRIC_CRITICAL": [
        r"infant", r"toddler", r"newborn", r"febrile\s*seizure", r"pediatric\s*emergency", r"child\s*unresponsive"
    ]
}


class EmergencyClassifier:
    """Intelligent classification and triage engine for AEGIS."""

    @classmethod
    def classify(
        cls,
        chief_complaint: str,
        patient_age: Optional[int] = None,
        patient_gender: Optional[str] = None,
        vitals_bp: Optional[str] = None,
        vitals_hr: Optional[int] = None,
        vitals_spo2: Optional[int] = None,
        vitals_gcs: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Analyzes complaint text, demographics, and vitals to determine category, severity,

        and required hospital capabilities.
        """
        text = (chief_complaint or "").lower()
        
        # 1. Age-based triage routing check
        is_pediatric = patient_age is not None and patient_age < 14
        
        # 2. Score category keywords
        matched_category = "GENERAL_MEDICAL"
        best_match_count = 0
        
        for category, patterns in KEYWORD_PATTERNS.items():
            matches = 0
            for pattern in patterns:
                if re.search(pattern, text):
                    matches += 1
            if matches > best_match_count:
                best_match_count = matches
                matched_category = category
        
        if is_pediatric and matched_category in ["GENERAL_MEDICAL", "PEDIATRIC_CRITICAL"]:
            matched_category = "PEDIATRIC_CRITICAL"

        # 3. Analyze vital signs for physiological instability
        risk_flags: List[str] = []
        is_instability_critical = False
        is_instability_urgent = False
        
        # Blood pressure check
        if vitals_bp:
            try:
                systolic = int(vitals_bp.split("/")[0].strip())
                if systolic < 90:
                    risk_flags.append(f"Severe Hypotension (Systolic {systolic} mmHg)")
                    is_instability_critical = True
                elif systolic > 180:
                    risk_flags.append(f"Hypertensive Crisis (Systolic {systolic} mmHg)")
                    is_instability_urgent = True
            except Exception:
                pass
        
        # Heart rate check
        if vitals_hr is not None:
            if vitals_hr > 130 or vitals_hr < 45:
                risk_flags.append(f"Dangerous Heart Rate ({vitals_hr} BPM)")
                is_instability_critical = True
            elif vitals_hr > 110 or vitals_hr < 55:
                risk_flags.append(f"Abnormal Heart Rate ({vitals_hr} BPM)")
                is_instability_urgent = True
        
        # SpO2 oxygen saturation check
        if vitals_spo2 is not None:
            if vitals_spo2 < 88:
                risk_flags.append(f"Severe Hypoxemia (SpO2 {vitals_spo2}%)")
                is_instability_critical = True
            elif vitals_spo2 < 92:
                risk_flags.append(f"Moderate Hypoxemia (SpO2 {vitals_spo2}%)")
                is_instability_urgent = True

        # GCS (Glasgow Coma Scale) check: 3-15
        if vitals_gcs is not None:
            if vitals_gcs <= 8:
                risk_flags.append(f"Coma/Severe Neurological Deficit (GCS {vitals_gcs}/15)")
                is_instability_critical = True
            elif vitals_gcs <= 12:
                risk_flags.append(f"Altered Mental Status (GCS {vitals_gcs}/15)")
                is_instability_urgent = True

        # 4. Severity Assignment
        critical_categories = ["CARDIAC_ARREST", "POLYTRAUMA", "ACUTE_STROKE", "RESPIRATORY_FAILURE"]
        if is_instability_critical or matched_category in critical_categories:
            severity = "CRITICAL"
        elif is_instability_urgent or matched_category in ["SEVERE_BURN", "PEDIATRIC_CRITICAL"]:
            severity = "URGENT"
        elif "mild" in text or "stable" in text or "minor" in text:
            severity = "MODERATE"
        else:
            severity = "URGENT"

        # 5. Extract requirements
        reqs = CATEGORY_REQUIREMENTS.get(matched_category, CATEGORY_REQUIREMENTS["GENERAL_MEDICAL"])
        required_specialties = list(reqs["specialties"])
        required_resources = list(reqs["resources"])

        # 6. Synthesize AI explanation
        summary_points = [
            f"Classified as {matched_category.replace('_', ' ')} with {severity} priority based on clinical symptom profile."
        ]
        if risk_flags:
            summary_points.append("Physiological alerts: " + "; ".join(risk_flags))
        if reqs.get("needs_cath_lab"):
            summary_points.append("Immediate percutaneous coronary intervention (PCI/Cath Lab) designated as critical requirement.")
        if reqs.get("needs_stroke_center"):
            summary_points.append("Primary Stroke Center with rapid CT angiography and thrombectomy capabilities mandatory.")
        if matched_category == "POLYTRAUMA":
            summary_points.append("Level 1 Trauma Center with immediate surgical bays and massive transfusion protocol needed.")

        ai_classification_text = " | ".join(summary_points)

        return {
            "category": matched_category,
            "severity": severity,
            "required_specialties": required_specialties,
            "required_resources": required_resources,
            "ai_classification": ai_classification_text,
            "risk_flags": risk_flags,
            "needs_cath_lab": reqs.get("needs_cath_lab", False),
            "needs_stroke_center": reqs.get("needs_stroke_center", False),
        }
