CREATE TABLE IF NOT EXISTS documents (
    id VARCHAR PRIMARY KEY,
    original_filename VARCHAR NOT NULL,
    doc_type VARCHAR NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    status VARCHAR NOT NULL,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS pages (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_no INTEGER NOT NULL,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS artifacts (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    searchable_pdf_path VARCHAR,
    json_path VARCHAR,
    extracted_json JSONB
);
