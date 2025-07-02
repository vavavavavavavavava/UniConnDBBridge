CREATE TABLE sample_table (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    value INT
);

INSERT INTO sample_table (name, value) VALUES ('test1', 100), ('test2', 200);
