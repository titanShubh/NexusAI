-- ── CLEANUP PREVIOUS TABLES ──────────────────────────────────────────
DROP TABLE IF EXISTS sales;
DROP TABLE IF EXISTS employees;
DROP TABLE IF EXISTS customers;

-- ── CUSTOMERS TABLE ──────────────────────────────────────────────────
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    segment VARCHAR(50) NOT NULL, -- Retail, Enterprise, SMB
    lifetime_value NUMERIC(10, 2) DEFAULT 0.00
);

-- ── EMPLOYEES TABLE ──────────────────────────────────────────────────
CREATE TABLE employees (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    department VARCHAR(50) NOT NULL, -- Sales, Marketing, Engineering, HR, Finance
    salary NUMERIC(10, 2) NOT NULL,
    hire_date DATE NOT NULL
);

-- ── SALES TABLE ──────────────────────────────────────────────────────
CREATE TABLE sales (
    id SERIAL PRIMARY KEY,
    product VARCHAR(100) NOT NULL,
    region VARCHAR(50) NOT NULL, -- East, West, North, South
    amount NUMERIC(10, 2) NOT NULL,
    date DATE NOT NULL,
    customer_id INT REFERENCES customers(id) ON DELETE SET NULL
);

-- ── SEED CUSTOMERS ───────────────────────────────────────────────────
INSERT INTO customers (name, email, segment, lifetime_value) VALUES
('John Doe', 'john.doe@retail.com', 'Retail', 1250.50),
('Jane Smith', 'jane.smith@enterprise.com', 'Enterprise', 45000.00),
('Bob Johnson', 'bob.johnson@smb.com', 'SMB', 8200.00),
('Alice Brown', 'alice.brown@retail.com', 'Retail', 350.00),
('Charlie Green', 'charlie.green@enterprise.com', 'Enterprise', 120000.00),
('David White', 'david.white@smb.com', 'SMB', 5400.20),
('Eva Black', 'eva.black@retail.com', 'Retail', 95.50),
('Frank Harris', 'frank.harris@retail.com', 'Retail', 1450.00),
('Grace Lee', 'grace.lee@enterprise.com', 'Enterprise', 85000.00),
('Henry Wilson', 'henry.wilson@smb.com', 'SMB', 12500.00),
('Ivy Taylor', 'ivy.taylor@retail.com', 'Retail', 420.00),
('Jack Miller', 'jack.miller@smb.com', 'SMB', 7800.00),
('Karen Davis', 'karen.davis@retail.com', 'Retail', 210.00),
('Leo Garcia', 'leo.garcia@enterprise.com', 'Enterprise', 32000.00),
('Mia Martinez', 'mia.martinez@smb.com', 'SMB', 6100.00);

-- ── SEED EMPLOYEES ───────────────────────────────────────────────────
INSERT INTO employees (name, department, salary, hire_date) VALUES
('Alice Adams', 'Sales', 65000.00, '2021-03-15'),
('Brad Baker', 'Sales', 58000.00, '2022-06-01'),
('Chloe Carter', 'Marketing', 62000.00, '2020-11-10'),
('Dan Davis', 'Engineering', 95000.00, '2019-04-22'),
('Emily Evans', 'Engineering', 105000.00, '2018-08-01'),
('Fred Foster', 'HR', 55000.00, '2023-01-15'),
('Grace Gray', 'Finance', 75000.00, '2021-09-01'),
('Harry Hill', 'Sales', 60000.00, '2022-10-15'),
('Iris Ince', 'Engineering', 92000.00, '2021-05-10'),
('Jack Jones', 'Engineering', 110000.00, '2017-02-15'),
('Kate King', 'Marketing', 64000.00, '2022-02-01'),
('Luke Lewis', 'Finance', 72000.00, '2023-05-01'),
('Mona Moore', 'HR', 57000.00, '2022-08-15'),
('Ned Nelson', 'Sales', 63000.00, '2021-12-01'),
('Olivia Owen', 'Engineering', 98000.00, '2020-03-15');

-- ── SEED SALES ───────────────────────────────────────────────────────
INSERT INTO sales (product, region, amount, date, customer_id) VALUES
('SaaS Subscription Enterprise', 'East', 15000.00, '2026-01-05', 2),
('Hardware Server Bundle', 'West', 30000.00, '2026-01-12', 5),
('Standard Software License', 'North', 1200.00, '2026-01-18', 1),
('Consulting Package Medium', 'South', 8200.00, '2026-01-22', 3),
('Standard Software License', 'East', 1200.00, '2026-01-28', 4),
('SaaS Subscription Enterprise', 'North', 25000.00, '2026-02-02', 9),
('Hardware Server Bundle', 'South', 15000.00, '2026-02-10', 6),
('Consulting Package Medium', 'West', 5400.00, '2026-02-15', 6),
('Support Contract Annual', 'East', 3200.00, '2026-02-20', 10),
('Standard Software License', 'West', 1200.00, '2026-02-25', 11),
('SaaS Subscription Enterprise', 'South', 32000.00, '2026-03-01', 14),
('Hardware Server Bundle', 'East', 15000.00, '2026-03-08', 9),
('Consulting Package Medium', 'North', 7800.00, '2026-03-12', 12),
('Support Contract Annual', 'West', 3200.00, '2026-03-18', 13),
('Standard Software License', 'South', 1200.00, '2026-03-24', 7),
('SaaS Subscription Enterprise', 'West', 20000.00, '2026-04-02', 5),
('Hardware Server Bundle', 'North', 15000.00, '2026-04-08', 10),
('Consulting Package Medium', 'East', 6100.00, '2026-04-15', 15),
('Support Contract Annual', 'South', 3200.00, '2026-04-20', 10),
('Standard Software License', 'North', 1200.00, '2026-04-26', 1);
