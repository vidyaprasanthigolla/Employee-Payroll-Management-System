-- =====================================================================
-- DATABASE SCHEMA: EMPLOYEE PAYROLL MANAGEMENT SYSTEM
-- Target DBMS: MySQL 8.0+
-- Engine: InnoDB
-- Character Set: utf8mb4 / utf8mb4_unicode_ci
-- =====================================================================

CREATE DATABASE IF NOT EXISTS `payroll_db` 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE `payroll_db`;

-- Drop existing tables in reverse dependency order if rebuilding
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS `audit_logs`;
DROP TABLE IF EXISTS `payslips`;
DROP TABLE IF EXISTS `payroll_details`;
DROP TABLE IF EXISTS `payroll`;
DROP TABLE IF EXISTS `employee_salary_components`;
DROP TABLE IF EXISTS `salary_structures`;
DROP TABLE IF EXISTS `salary_components`;
DROP TABLE IF EXISTS `leave_requests`;
DROP TABLE IF EXISTS `leave_balances`;
DROP TABLE IF EXISTS `attendance`;
DROP TABLE IF EXISTS `employees`;
DROP TABLE IF EXISTS `designations`;
DROP TABLE IF EXISTS `departments`;
DROP TABLE IF EXISTS `users`;
SET FOREIGN_KEY_CHECKS = 1;

-- =====================================================================
-- 1. USERS TABLE
-- Authentication and Role-Based Access Control
-- =====================================================================
CREATE TABLE `users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `username` VARCHAR(50) NOT NULL UNIQUE,
    `email` VARCHAR(100) NOT NULL UNIQUE,
    `password_hash` VARCHAR(255) NOT NULL,
    `role` ENUM('ADMIN', 'HR', 'EMPLOYEE') NOT NULL DEFAULT 'EMPLOYEE',
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_users_role` (`role`),
    INDEX `idx_users_is_active` (`is_active`)
) ENGINE=InnoDB;

-- =====================================================================
-- 2. DEPARTMENTS TABLE
-- Organizational Divisions
-- =====================================================================
CREATE TABLE `departments` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(100) NOT NULL UNIQUE,
    `description` VARCHAR(255) NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- =====================================================================
-- 3. DESIGNATIONS TABLE
-- Job Titles and Organizational Hierarchies
-- =====================================================================
CREATE TABLE `designations` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `title` VARCHAR(100) NOT NULL UNIQUE,
    `department_id` INT NULL,
    `description` VARCHAR(255) NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_designation_department`
        FOREIGN KEY (`department_id`) REFERENCES `departments` (`id`)
        ON DELETE SET NULL ON UPDATE CASCADE,
    INDEX `idx_designation_department` (`department_id`)
) ENGINE=InnoDB;

-- =====================================================================
-- 4. EMPLOYEES TABLE
-- Comprehensive Employee Master Profile
-- =====================================================================
CREATE TABLE `employees` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `employee_code` VARCHAR(20) NOT NULL UNIQUE,
    `user_id` INT NOT NULL UNIQUE,
    `first_name` VARCHAR(50) NOT NULL,
    `last_name` VARCHAR(50) NOT NULL,
    `phone` VARCHAR(20) NOT NULL,
    `address` TEXT NULL,
    `date_of_birth` DATE NOT NULL,
    `gender` ENUM('MALE', 'FEMALE', 'OTHER') NOT NULL,
    `date_of_joining` DATE NOT NULL,
    `department_id` INT NULL,
    `designation_id` INT NULL,
    `employment_type` ENUM('FULL_TIME', 'PART_TIME', 'CONTRACT', 'INTERN') NOT NULL DEFAULT 'FULL_TIME',
    `bank_name` VARCHAR(100) NOT NULL,
    `bank_account_number` VARCHAR(50) NOT NULL,
    `ifsc_code` VARCHAR(20) NOT NULL,
    `pan_number` VARCHAR(20) NOT NULL,
    `status` ENUM('ACTIVE', 'PROBATION', 'RESIGNED', 'TERMINATED') NOT NULL DEFAULT 'ACTIVE',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_employee_user`
        FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_employee_department`
        FOREIGN KEY (`department_id`) REFERENCES `departments` (`id`)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT `fk_employee_designation`
        FOREIGN KEY (`designation_id`) REFERENCES `designations` (`id`)
        ON DELETE SET NULL ON UPDATE CASCADE,
    INDEX `idx_employees_status` (`status`),
    INDEX `idx_employees_dept` (`department_id`),
    INDEX `idx_employees_desig` (`designation_id`),
    INDEX `idx_employees_joining` (`date_of_joining`)
) ENGINE=InnoDB;

-- =====================================================================
-- 5. ATTENDANCE TABLE
-- Daily Attendance and Work Hour Tracking
-- =====================================================================
CREATE TABLE `attendance` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `employee_id` INT NOT NULL,
    `date` DATE NOT NULL,
    `status` ENUM('PRESENT', 'ABSENT', 'HALF_DAY', 'ON_LEAVE', 'HOLIDAY') NOT NULL DEFAULT 'PRESENT',
    `check_in` TIME NULL,
    `check_out` TIME NULL,
    `working_hours` DECIMAL(4, 2) NOT NULL DEFAULT 0.00,
    `remarks` VARCHAR(255) NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_attendance_employee`
        FOREIGN KEY (`employee_id`) REFERENCES `employees` (`id`)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `uq_employee_attendance_date`
        UNIQUE (`employee_id`, `date`),
    INDEX `idx_attendance_date` (`date`),
    INDEX `idx_attendance_status` (`status`)
) ENGINE=InnoDB;

-- =====================================================================
-- 6. LEAVE_BALANCES TABLE
-- Annual Available and Consumed Leave Quota
-- =====================================================================
CREATE TABLE `leave_balances` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `employee_id` INT NOT NULL,
    `year` INT NOT NULL,
    `leave_type` ENUM('CASUAL', 'SICK', 'EARNED', 'UNPAID') NOT NULL,
    `total_allocated` DECIMAL(4, 1) NOT NULL DEFAULT 0.0,
    `used` DECIMAL(4, 1) NOT NULL DEFAULT 0.0,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_leave_balances_employee`
        FOREIGN KEY (`employee_id`) REFERENCES `employees` (`id`)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `uq_employee_leave_type_year`
        UNIQUE (`employee_id`, `year`, `leave_type`),
    INDEX `idx_leave_balances_year` (`year`)
) ENGINE=InnoDB;

-- =====================================================================
-- 7. LEAVE_REQUESTS TABLE
-- Employee Leave Applications and HR Approval Workflow
-- =====================================================================
CREATE TABLE `leave_requests` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `employee_id` INT NOT NULL,
    `leave_type` ENUM('CASUAL', 'SICK', 'EARNED', 'UNPAID') NOT NULL,
    `start_date` DATE NOT NULL,
    `end_date` DATE NOT NULL,
    `days` DECIMAL(4, 1) NOT NULL,
    `reason` TEXT NOT NULL,
    `status` ENUM('PENDING', 'APPROVED', 'REJECTED') NOT NULL DEFAULT 'PENDING',
    `reviewed_by` INT NULL,
    `reviewed_at` DATETIME NULL,
    `admin_remarks` VARCHAR(255) NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_leave_requests_employee`
        FOREIGN KEY (`employee_id`) REFERENCES `employees` (`id`)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_leave_requests_reviewer`
        FOREIGN KEY (`reviewed_by`) REFERENCES `users` (`id`)
        ON DELETE SET NULL ON UPDATE CASCADE,
    INDEX `idx_leave_requests_status` (`status`),
    INDEX `idx_leave_requests_dates` (`start_date`, `end_date`)
) ENGINE=InnoDB;

-- =====================================================================
-- 8. SALARY_COMPONENTS TABLE
-- Dynamic Definition of Earnings and Deductions
-- =====================================================================
CREATE TABLE `salary_components` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(50) NOT NULL UNIQUE,
    `code` VARCHAR(20) NOT NULL UNIQUE,
    `type` ENUM('EARNING', 'DEDUCTION') NOT NULL,
    `calculation_type` ENUM('FLAT', 'PERCENTAGE') NOT NULL DEFAULT 'FLAT',
    `is_taxable` BOOLEAN NOT NULL DEFAULT TRUE,
    `is_statutory` BOOLEAN NOT NULL DEFAULT FALSE,
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
    `description` VARCHAR(255) NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_components_type` (`type`),
    INDEX `idx_components_active` (`is_active`)
) ENGINE=InnoDB;

-- =====================================================================
-- 9. SALARY_STRUCTURES TABLE
-- Master Structure Grades / Frameworks
-- =====================================================================
CREATE TABLE `salary_structures` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(100) NOT NULL UNIQUE,
    `description` VARCHAR(255) NULL,
    `base_monthly_salary` DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- =====================================================================
-- 10. EMPLOYEE_SALARY_COMPONENTS TABLE
-- Individualized Component Values Assigned to Employees
-- =====================================================================
CREATE TABLE `employee_salary_components` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `employee_id` INT NOT NULL,
    `component_id` INT NOT NULL,
    `amount` DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    `percentage` DECIMAL(5, 2) NULL,
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
    `effective_from` DATE NOT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_emp_sal_comp_emp`
        FOREIGN KEY (`employee_id`) REFERENCES `employees` (`id`)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_emp_sal_comp_component`
        FOREIGN KEY (`component_id`) REFERENCES `salary_components` (`id`)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT `uq_emp_salary_component`
        UNIQUE (`employee_id`, `component_id`),
    INDEX `idx_emp_sal_comp_active` (`is_active`)
) ENGINE=InnoDB;

-- =====================================================================
-- 11. PAYROLL TABLE
-- Monthly Processed Payroll Summaries (Prevent Duplicate Processing)
-- =====================================================================
CREATE TABLE `payroll` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `payroll_batch_code` VARCHAR(50) NOT NULL,
    `employee_id` INT NOT NULL,
    `month` TINYINT NOT NULL CHECK (`month` BETWEEN 1 AND 12),
    `year` SMALLINT NOT NULL CHECK (`year` >= 2000),
    `payable_days` DECIMAL(4, 1) NOT NULL DEFAULT 30.0,
    `present_days` DECIMAL(4, 1) NOT NULL DEFAULT 0.0,
    `paid_leaves` DECIMAL(4, 1) NOT NULL DEFAULT 0.0,
    `unpaid_leaves` DECIMAL(4, 1) NOT NULL DEFAULT 0.0,
    `gross_salary` DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    `total_deductions` DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    `lop_deduction` DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    `net_salary` DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    `status` ENUM('DRAFT', 'APPROVED', 'PAID', 'REJECTED') NOT NULL DEFAULT 'DRAFT',
    `processed_by` INT NULL,
    `approved_by` INT NULL,
    `payment_date` DATE NULL,
    `payment_method` ENUM('BANK_TRANSFER', 'CHEQUE', 'CASH') NOT NULL DEFAULT 'BANK_TRANSFER',
    `remarks` TEXT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_payroll_employee`
        FOREIGN KEY (`employee_id`) REFERENCES `employees` (`id`)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT `fk_payroll_processor`
        FOREIGN KEY (`processed_by`) REFERENCES `users` (`id`)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT `fk_payroll_approver`
        FOREIGN KEY (`approved_by`) REFERENCES `users` (`id`)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT `uq_employee_month_year`
        UNIQUE (`employee_id`, `month`, `year`),
    INDEX `idx_payroll_batch` (`payroll_batch_code`),
    INDEX `idx_payroll_status` (`status`),
    INDEX `idx_payroll_period` (`year`, `month`)
) ENGINE=InnoDB;

-- =====================================================================
-- 12. PAYROLL_DETAILS TABLE
-- Itemized Earning and Deduction Audit Line Items (Immutable Snapshot)
-- =====================================================================
CREATE TABLE `payroll_details` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `payroll_id` INT NOT NULL,
    `component_id` INT NOT NULL,
    `component_name` VARCHAR(100) NOT NULL,
    `component_type` ENUM('EARNING', 'DEDUCTION') NOT NULL,
    `amount` DECIMAL(12, 2) NOT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_payroll_details_payroll`
        FOREIGN KEY (`payroll_id`) REFERENCES `payroll` (`id`)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_payroll_details_component`
        FOREIGN KEY (`component_id`) REFERENCES `salary_components` (`id`)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    INDEX `idx_payroll_details_payroll` (`payroll_id`),
    INDEX `idx_payroll_details_type` (`component_type`)
) ENGINE=InnoDB;

-- =====================================================================
-- 13. PAYSLIPS TABLE
-- Generated PDF Artifacts and Tracking
-- =====================================================================
CREATE TABLE `payslips` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `payslip_number` VARCHAR(50) NOT NULL UNIQUE,
    `payroll_id` INT NOT NULL UNIQUE,
    `employee_id` INT NOT NULL,
    `month` TINYINT NOT NULL,
    `year` SMALLINT NOT NULL,
    `file_path` VARCHAR(255) NOT NULL,
    `generated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `download_count` INT NOT NULL DEFAULT 0,
    CONSTRAINT `fk_payslips_payroll`
        FOREIGN KEY (`payroll_id`) REFERENCES `payroll` (`id`)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_payslips_employee`
        FOREIGN KEY (`employee_id`) REFERENCES `employees` (`id`)
        ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX `idx_payslips_employee` (`employee_id`),
    INDEX `idx_payslips_period` (`year`, `month`)
) ENGINE=InnoDB;

-- =====================================================================
-- 14. AUDIT_LOGS TABLE
-- Security and Financial Audit Trail
-- =====================================================================
CREATE TABLE `audit_logs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NULL,
    `action` VARCHAR(50) NOT NULL,
    `entity_name` VARCHAR(50) NOT NULL,
    `entity_id` INT NULL,
    `old_values` JSON NULL,
    `new_values` JSON NULL,
    `ip_address` VARCHAR(45) NULL,
    `timestamp` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_audit_user`
        FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
        ON DELETE SET NULL ON UPDATE CASCADE,
    INDEX `idx_audit_user` (`user_id`),
    INDEX `idx_audit_action` (`action`),
    INDEX `idx_audit_entity` (`entity_name`, `entity_id`),
    INDEX `idx_audit_timestamp` (`timestamp`)
) ENGINE=InnoDB;
