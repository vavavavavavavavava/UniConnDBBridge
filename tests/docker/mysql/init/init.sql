CREATE DATABASE IF NOT EXISTS testdb;
DROP USER IF EXISTS 'testuser'@'localhost';
DROP USER IF EXISTS 'testuser'@'%';
DROP USER IF EXISTS 'testuser'@'127.0.0.1';
DROP USER IF EXISTS 'testuser'@':;1';
CREATE USER 'testuser'@'127.0.0.1' IDENTIFIED WITH mysql_native_password BY 'testpassword';
GRANT ALL PRIVILEGES ON testdb.* TO 'testuser'@'127.0.0.1';
CREATE USER 'testuser'@':;1' IDENTIFIED WITH mysql_native_password BY 'testpassword';
GRANT ALL PRIVILEGES ON testdb.* TO 'testuser'@':;1';
FLUSH PRIVILEGES;

USE testdb;

CREATE TABLE sample_table (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    value INT
);

INSERT INTO sample_table (name, value) VALUES ('test1', 100), ('test2', 200);
