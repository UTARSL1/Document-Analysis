-- Initial database schema for document digitization system
-- This creates the core tables with partitioning support

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Documents table with partitioning by document type
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    original_filename VARCHAR(512) NOT NULL,
    doc_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'ingested',
    batch_id VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    error_message TEXT,
    file_size_bytes BIGINT,
    storage_backend VARCHAR(50) NOT NULL,
    original_path VARCHAR(1024)
);

-- Note: Partitioning by doc_type would be done after knowing all 12-16 types
-- For now, create indexes for performance
CREATE INDEX idx_documents_doc_type ON documents(doc_type);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_batch_id ON documents(batch_id);
CREATE INDEX idx_documents_created_at ON documents(created_at);

-- QC Verification table
CREATE TABLE qc_verification (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    qc_status VARCHAR(50) NOT NULL,
    resolution_dpi INTEGER,
    skew_angle FLOAT,
    contrast_score FLOAT,
    border_check_passed BOOLEAN,
    completeness_check_passed BOOLEAN,
    evidence_path VARCHAR(1024),
    evidence_json JSONB,
    verified_at TIMESTAMP NOT NULL DEFAULT NOW(),
    verified_by VARCHAR(255),
    notes TEXT
);

CREATE INDEX idx_qc_verification_document_id ON qc_verification(document_id);
CREATE INDEX idx_qc_verification_status ON qc_verification(qc_status);

-- Correction Log table
CREATE TABLE correction_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    correction_type VARCHAR(100) NOT NULL,
    operator_id VARCHAR(255),
    before_path VARCHAR(1024),
    after_path VARCHAR(1024),
    correction_params JSONB,
    corrected_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_correction_log_document_id ON correction_log(document_id);

-- Templates table
CREATE TABLE templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    doc_type VARCHAR(100) NOT NULL UNIQUE,
    version INTEGER NOT NULL DEFAULT 1,
    zones JSONB NOT NULL,
    validation_rules JSONB,
    anchor_points JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);

CREATE INDEX idx_templates_doc_type ON templates(doc_type);

-- Zone Data table (extracted OCR/HTR data per zone)
CREATE TABLE zone_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    zone_name VARCHAR(255) NOT NULL,
    extracted_text TEXT,
    confidence FLOAT,
    bbox INTEGER[],
    validation_status VARCHAR(50),
    parsed_value JSONB,
    is_handwritten BOOLEAN,
    extracted_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_zone_data_document_id ON zone_data(document_id);
CREATE INDEX idx_zone_data_validation_status ON zone_data(validation_status);

-- Artifacts table
CREATE TABLE artifacts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    searchable_pdf_path VARCHAR(1024),
    json_path VARCHAR(1024),
    json_data JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_artifacts_document_id ON artifacts(document_id);
CREATE INDEX idx_artifacts_json_data ON artifacts USING GIN(json_data);

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_templates_updated_at BEFORE UPDATE ON templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
