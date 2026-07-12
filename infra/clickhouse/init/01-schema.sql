CREATE DATABASE IF NOT EXISTS data_warehouse;

CREATE USER IF NOT EXISTS chatbi_reader
IDENTIFIED WITH sha256_password BY 'chatbi_reader_dev';

GRANT SELECT ON data_warehouse.* TO chatbi_reader;
