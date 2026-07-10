CREATE SCHEMA IF NOT EXISTS metric_center;
CREATE SCHEMA IF NOT EXISTS audit;
CREATE SCHEMA IF NOT EXISTS app;

COMMENT ON SCHEMA metric_center IS 'Metric, dimension, semantic model, and version metadata';
COMMENT ON SCHEMA audit IS 'Query, approval, evidence, and feedback audit records';
COMMENT ON SCHEMA app IS 'Application context and conversation metadata';

