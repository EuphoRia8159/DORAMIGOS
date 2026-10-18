"""AEGIS Database Engine and Session Management."""

import logging
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from aegis_backend.config import settings

logger = logging.getLogger(__name__)

# Handle SQLite-specific connect args
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency that provides an active database session for request scopes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def migrate_db() -> None:
    """Applies non-destructive schema migrations for existing SQLite database."""
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(hospitals);")).fetchall()
            existing_cols = {row[1] for row in result}
            
            new_columns = [
                ("state", "VARCHAR(100)"),
                ("district", "VARCHAR(100)"),
                ("pincode", "VARCHAR(20)"),
                ("data_source", "VARCHAR(30) DEFAULT 'SIMULATED'"),
                ("is_live_monitored", "BOOLEAN DEFAULT 0"),
                ("facilities_json", "TEXT DEFAULT '[]'")
            ]
            
            for col_name, col_type in new_columns:
                if col_name not in existing_cols:
                    conn.execute(text(f"ALTER TABLE hospitals ADD COLUMN {col_name} {col_type};"))
                    logger.info("Added column %s to hospitals table.", col_name)
            
            # Check if latitude column has NOT NULL constraint
            lat_col = [row for row in result if row[1] == "latitude"]
            if lat_col and lat_col[0][3] == 1:
                logger.info("Migrating hospitals schema to allow nullable coordinates...")
                conn.execute(text("PRAGMA foreign_keys=OFF;"))
                conn.execute(text("""
                CREATE TABLE IF NOT EXISTS hospitals_temp (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    code VARCHAR(50) NOT NULL UNIQUE,
                    address VARCHAR(500) NOT NULL,
                    latitude FLOAT,
                    longitude FLOAT,
                    contact_phone VARCHAR(100) NOT NULL,
                    trauma_level VARCHAR(50) DEFAULT 'Level 2',
                    specialties_json TEXT DEFAULT '[]',
                    facilities_json TEXT DEFAULT '[]',
                    state VARCHAR(100),
                    district VARCHAR(100),
                    pincode VARCHAR(20),
                    data_source VARCHAR(30) DEFAULT 'SIMULATED',
                    is_live_monitored BOOLEAN DEFAULT 0,
                    total_beds INTEGER DEFAULT 100,
                    available_beds INTEGER DEFAULT 20,
                    icu_total INTEGER DEFAULT 20,
                    icu_available INTEGER DEFAULT 5,
                    er_capacity INTEGER DEFAULT 30,
                    er_current_load INTEGER DEFAULT 15,
                    has_cath_lab BOOLEAN DEFAULT 0,
                    has_stroke_center BOOLEAN DEFAULT 0,
                    has_ct_scanner BOOLEAN DEFAULT 1,
                    has_mri BOOLEAN DEFAULT 0,
                    has_burn_unit BOOLEAN DEFAULT 0,
                    has_pediatric_icu BOOLEAN DEFAULT 0,
                    has_hyperbaric_chamber BOOLEAN DEFAULT 0,
                    status VARCHAR(30) DEFAULT 'OPERATIONAL',
                    ibm_z_connected BOOLEAN DEFAULT 0,
                    ibm_z_node_id VARCHAR(50) DEFAULT 'SYS1-ZOS-CICS',
                    last_ibm_z_sync DATETIME,
                    created_at DATETIME,
                    updated_at DATETIME
                );
                """))
                conn.execute(text("""
                INSERT INTO hospitals_temp (
                    id, name, code, address, latitude, longitude, contact_phone, trauma_level,
                    specialties_json, facilities_json, state, district, pincode, data_source,
                    is_live_monitored, total_beds, available_beds, icu_total, icu_available,
                    er_capacity, er_current_load, has_cath_lab, has_stroke_center, has_ct_scanner,
                    has_mri, has_burn_unit, has_pediatric_icu, has_hyperbaric_chamber, status,
                    ibm_z_connected, ibm_z_node_id, last_ibm_z_sync, created_at, updated_at
                )
                SELECT
                    id, name, code, address, latitude, longitude, contact_phone, trauma_level,
                    specialties_json, facilities_json, state, district, pincode, data_source,
                    is_live_monitored, total_beds, available_beds, icu_total, icu_available,
                    er_capacity, er_current_load, has_cath_lab, has_stroke_center, has_ct_scanner,
                    has_mri, has_burn_unit, has_pediatric_icu, has_hyperbaric_chamber, status,
                    ibm_z_connected, ibm_z_node_id, last_ibm_z_sync, created_at, updated_at
                FROM hospitals;
                """))
                conn.execute(text("DROP TABLE hospitals;"))
                conn.execute(text("ALTER TABLE hospitals_temp RENAME TO hospitals;"))
                conn.execute(text("PRAGMA foreign_keys=ON;"))

            # Ensure indexes are created for hospitals
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_hospitals_id ON hospitals (id);"))
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_hospitals_code ON hospitals (code);"))
            conn.execute(text("DROP INDEX IF EXISTS ix_hospitals_name;"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_hospitals_name ON hospitals (name);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_hospitals_state ON hospitals (state);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_hospitals_district ON hospitals (district);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_hospitals_data_source ON hospitals (data_source);"))

            # Check hospital_recommendations table for nullable distance_km
            rec_result = conn.execute(text("PRAGMA table_info(hospital_recommendations);")).fetchall()
            rec_dist = [row for row in rec_result if row[1] == "distance_km"]
            if rec_dist and rec_dist[0][3] == 1:
                logger.info("Migrating hospital_recommendations schema to allow nullable distance and transit...")
                conn.execute(text("PRAGMA foreign_keys=OFF;"))
                conn.execute(text("""
                CREATE TABLE IF NOT EXISTS hospital_recommendations_temp (
                    id INTEGER PRIMARY KEY,
                    emergency_id INTEGER NOT NULL,
                    hospital_id INTEGER NOT NULL,
                    rank INTEGER NOT NULL,
                    composite_score FLOAT NOT NULL,
                    capability_score FLOAT DEFAULT 0.0,
                    transit_score FLOAT DEFAULT 0.0,
                    bed_score FLOAT DEFAULT 0.0,
                    congestion_penalty FLOAT DEFAULT 0.0,
                    ibm_z_bonus FLOAT DEFAULT 0.0,
                    distance_km FLOAT,
                    estimated_transit_minutes FLOAT,
                    rationale TEXT NOT NULL,
                    ibm_z_verified BOOLEAN DEFAULT 0,
                    status VARCHAR(30) DEFAULT 'RECOMMENDED',
                    created_at DATETIME
                );
                """))
                conn.execute(text("""
                INSERT INTO hospital_recommendations_temp (
                    id, emergency_id, hospital_id, rank, composite_score,
                    capability_score, transit_score, bed_score, congestion_penalty,
                    ibm_z_bonus, distance_km, estimated_transit_minutes, rationale,
                    ibm_z_verified, status, created_at
                )
                SELECT
                    id, emergency_id, hospital_id, rank, composite_score,
                    capability_score, transit_score, bed_score, congestion_penalty,
                    ibm_z_bonus, distance_km, estimated_transit_minutes, rationale,
                    ibm_z_verified, status, created_at
                FROM hospital_recommendations;
                """))
                conn.execute(text("DROP TABLE hospital_recommendations;"))
                conn.execute(text("ALTER TABLE hospital_recommendations_temp RENAME TO hospital_recommendations;"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_hospital_recommendations_id ON hospital_recommendations (id);"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_hospital_recommendations_emergency_id ON hospital_recommendations (emergency_id);"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_hospital_recommendations_hospital_id ON hospital_recommendations (hospital_id);"))
                conn.execute(text("PRAGMA foreign_keys=ON;"))

            conn.commit()
    except Exception as e:
        logger.warning("Database migration notice: %s", e)


def init_db() -> None:
    """Create all tables in the database if they do not exist and apply migrations."""
    # Import all models before create_all
    import aegis_backend.models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    migrate_db()
    logger.info("Database initialized successfully.")
