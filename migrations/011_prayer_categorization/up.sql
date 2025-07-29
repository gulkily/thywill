-- Add prayer categorization fields to prayer table
-- Migration 011: prayer_categorization

-- Safety filtering fields
ALTER TABLE prayer ADD COLUMN safety_score REAL DEFAULT 1.0;
ALTER TABLE prayer ADD COLUMN safety_flags TEXT DEFAULT '[]';
ALTER TABLE prayer ADD COLUMN categorization_method VARCHAR(20) DEFAULT 'default';

-- Classification fields
ALTER TABLE prayer ADD COLUMN specificity_type VARCHAR(20) DEFAULT 'unknown';
ALTER TABLE prayer ADD COLUMN specificity_confidence REAL DEFAULT 0.0;
ALTER TABLE prayer ADD COLUMN subject_category VARCHAR(50) DEFAULT 'general';

-- Create indexes for efficient filtering
CREATE INDEX IF NOT EXISTS idx_prayer_safety ON prayer(safety_score);
CREATE INDEX IF NOT EXISTS idx_prayer_categories ON prayer(specificity_type, subject_category, safety_score);
CREATE INDEX IF NOT EXISTS idx_prayer_category ON prayer(subject_category);

-- Initialize existing prayers with safe defaults
UPDATE prayer SET 
    safety_score = 1.0,
    safety_flags = '[]',
    categorization_method = 'default',
    specificity_type = 'unknown',
    specificity_confidence = 0.0,
    subject_category = 'general'
WHERE 
    safety_score IS NULL 
    OR safety_flags IS NULL 
    OR categorization_method IS NULL
    OR specificity_type IS NULL
    OR specificity_confidence IS NULL
    OR subject_category IS NULL;