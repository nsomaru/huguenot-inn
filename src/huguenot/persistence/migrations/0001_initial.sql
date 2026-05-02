-- Initial matter database schema and curated South African court seed data.
-- depends:

CREATE TABLE IF NOT EXISTS court_header_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    line TEXT NOT NULL UNIQUE,
    source TEXT NOT NULL DEFAULT 'seed'
);

CREATE TABLE IF NOT EXISTS courts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    default_header_line_id INTEGER REFERENCES court_header_lines(id),
    source TEXT NOT NULL DEFAULT 'seed'
);

CREATE TABLE IF NOT EXISTS matters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    court_id INTEGER NOT NULL REFERENCES courts(id),
    court_header_line_id INTEGER REFERENCES court_header_lines(id),
    proceeding_type TEXT NOT NULL CHECK (proceeding_type IN ('Action', 'Application')),
    case_number TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS parties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    matter_id INTEGER NOT NULL REFERENCES matters(id) ON DELETE CASCADE,
    side TEXT NOT NULL CHECK (side IN ('bringing', 'opposing')),
    name TEXT NOT NULL,
    position INTEGER NOT NULL,
    UNIQUE(matter_id, side, position)
);

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

INSERT OR IGNORE INTO court_header_lines(line, source) VALUES
    ('(CONSTITUTIONAL COURT OF SOUTH AFRICA)', 'judiciary.org.za'),
    ('(SUPREME COURT OF APPEAL)', 'judiciary.org.za'),
    ('(EASTERN CAPE DIVISION, GRAHAMSTOWN)', 'justice.gov.za'),
    ('(EASTERN CAPE LOCAL DIVISION, BHISHO)', 'justice.gov.za'),
    ('(EASTERN CAPE LOCAL DIVISION, MTHATHA)', 'justice.gov.za'),
    ('(EASTERN CAPE LOCAL DIVISION, GQEBERHA)', 'justice.gov.za'),
    ('(FREE STATE DIVISION, BLOEMFONTEIN)', 'justice.gov.za'),
    ('(GAUTENG DIVISION, PRETORIA)', 'justice.gov.za'),
    ('(GAUTENG LOCAL DIVISION, JOHANNESBURG)', 'justice.gov.za'),
    ('(KWAZULU-NATAL DIVISION, PIETERMARITZBURG)', 'justice.gov.za'),
    ('(KWAZULU-NATAL LOCAL DIVISION, DURBAN)', 'justice.gov.za'),
    ('(LIMPOPO DIVISION, POLOKWANE)', 'justice.gov.za'),
    ('(LIMPOPO LOCAL DIVISION, THOHOYANDOU)', 'justice.gov.za'),
    ('(MPUMALANGA DIVISION, MBOMBELA)', 'justice.gov.za'),
    ('(MPUMALANGA LOCAL DIVISION, MIDDELBURG)', 'justice.gov.za'),
    ('(NORTHERN CAPE DIVISION, KIMBERLEY)', 'justice.gov.za'),
    ('(NORTH WEST DIVISION, MAHIKENG)', 'justice.gov.za'),
    ('(WESTERN CAPE DIVISION, CAPE TOWN)', 'justice.gov.za'),
    ('(WESTERN CAPE LOCAL DIVISION, CAPE TOWN)', 'sample precedent'),
    ('(MAGISTRATES'' COURT)', 'seed pattern'),
    ('(REGIONAL COURT)', 'seed pattern'),
    ('(DISTRICT COURT)', 'seed pattern');

INSERT OR IGNORE INTO courts(name, default_header_line_id, source) VALUES
    ('IN THE CONSTITUTIONAL COURT OF SOUTH AFRICA', (SELECT id FROM court_header_lines WHERE line = '(CONSTITUTIONAL COURT OF SOUTH AFRICA)'), 'judiciary.org.za'),
    ('IN THE SUPREME COURT OF APPEAL OF SOUTH AFRICA', (SELECT id FROM court_header_lines WHERE line = '(SUPREME COURT OF APPEAL)'), 'judiciary.org.za'),
    ('IN THE HIGH COURT OF SOUTH AFRICA', (SELECT id FROM court_header_lines WHERE line = '(WESTERN CAPE DIVISION, CAPE TOWN)'), 'justice.gov.za'),
    ('IN THE HIGH COURT OF SOUTH AFRICA', (SELECT id FROM court_header_lines WHERE line = '(GAUTENG DIVISION, PRETORIA)'), 'justice.gov.za'),
    ('IN THE MAGISTRATES'' COURT FOR THE DISTRICT OF', (SELECT id FROM court_header_lines WHERE line = '(DISTRICT COURT)'), 'seed pattern'),
    ('IN THE REGIONAL COURT FOR THE REGIONAL DIVISION OF', (SELECT id FROM court_header_lines WHERE line = '(REGIONAL COURT)'), 'seed pattern');
