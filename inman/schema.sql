DROP TABLE IF EXISTS access;
DROP TABLE IF EXISTS asset_type;
DROP TABLE IF EXISTS company;
DROP TABLE IF EXISTS location;
DROP TABLE IF EXISTS status;
DROP TABLE IF EXISTS normal_service;
DROP TABLE IF EXISTS other_service;
DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS inventory;
DROP TABLE IF EXISTS link_normal_service;
DROP TABLE IF EXISTS link_other_service;

CREATE TABLE access (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL
);

CREATE TABLE asset_type (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL
);

CREATE TABLE company (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL
);

CREATE TABLE location (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL
);

CREATE TABLE status (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL
);

CREATE TABLE normal_service (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL
);

CREATE TABLE other_service (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL,
  remarks TEXT
);

CREATE TABLE user (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL,
  access INTEGER NOT NULL,
  FOREIGN KEY (access) REFERENCES access (id)
);

CREATE TABLE inventory (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  asset_no TEXT UNIQUE NOT NULL,
  asset_type INTEGER NOT NULL,
  company INTEGER NOT NULL,
  location INTEGER NOT NULL,
  status INTEGER NOT NULL,
  FOREIGN KEY (asset_type) REFERENCES asset_type (id),
  FOREIGN KEY (company) REFERENCES company (id),
  FOREIGN KEY (location) REFERENCES location (id),
  FOREIGN KEY (status) REFERENCES status (id)
);

CREATE TABLE link_normal_service (
  inventory_id INTEGER NOT NULL,
  normal_service_id INTEGER NOT NULL,
  FOREIGN KEY (inventory_id) REFERENCES inventory (id),
  FOREIGN KEY (normal_service_id) REFERENCES normal_service (id)
);

CREATE TABLE link_other_service (
  inventory_id INTEGER NOT NULL,
  other_service_id INTEGER NOT NULL,
  FOREIGN KEY (inventory_id) REFERENCES inventory (id),
  FOREIGN KEY (other_service_id) REFERENCES other_service (id)
);

INSERT INTO status VALUES (1, 'working');
INSERT INTO status VALUES (2, 'not-working');
INSERT INTO access VALUES (1, 'admin');
INSERT INTO access VALUES (2, 'regular');
