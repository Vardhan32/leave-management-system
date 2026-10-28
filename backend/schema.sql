-- MySQL 8 schema for LeaveDesk.
-- The Flask CLI creates these tables through SQLAlchemy as well.

CREATE DATABASE IF NOT EXISTS leave_desk
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE leave_desk;

CREATE TABLE IF NOT EXISTS users (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(255) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(20) NOT NULL DEFAULT 'employee',
  department VARCHAR(80) NULL,
  job_title VARCHAR(120) NULL,
  joined_on DATE NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_users_email (email),
  KEY ix_users_role (role)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS leave_types (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  code VARCHAR(20) NOT NULL,
  name VARCHAR(80) NOT NULL,
  default_days INT NOT NULL DEFAULT 0,
  description VARCHAR(255) NULL,
  sort_order INT NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  UNIQUE KEY uq_leave_types_code (code)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS leave_balances (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id INT UNSIGNED NOT NULL,
  leave_type_id INT UNSIGNED NOT NULL,
  year SMALLINT NOT NULL,
  allocated_days INT NOT NULL DEFAULT 0,
  used_days INT NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  UNIQUE KEY uq_balance_user_type_year (user_id, leave_type_id, year),
  KEY ix_leave_balances_year (year),
  CONSTRAINT fk_leave_balances_user
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
  CONSTRAINT fk_leave_balances_type
    FOREIGN KEY (leave_type_id) REFERENCES leave_types (id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS leave_requests (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id INT UNSIGNED NOT NULL,
  leave_type_id INT UNSIGNED NOT NULL,
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  days INT NOT NULL,
  reason TEXT NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  reviewed_by_id INT UNSIGNED NULL,
  reviewed_at DATETIME NULL,
  review_note TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_leave_requests_user_status (user_id, status),
  KEY ix_leave_requests_dates (start_date, end_date),
  CONSTRAINT ck_leave_requests_status
    CHECK (status IN ('pending', 'approved', 'rejected', 'cancelled')),
  CONSTRAINT fk_leave_requests_user
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
  CONSTRAINT fk_leave_requests_type
    FOREIGN KEY (leave_type_id) REFERENCES leave_types (id),
  CONSTRAINT fk_leave_requests_reviewer
    FOREIGN KEY (reviewed_by_id) REFERENCES users (id) ON DELETE SET NULL
) ENGINE=InnoDB;
