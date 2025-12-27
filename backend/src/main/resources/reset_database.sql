-- ========================================
-- 完全重置数据库脚本
-- ========================================

-- 强制删除数据库（会删除所有数据）
DROP DATABASE IF EXISTS lab_management;

-- 重新创建数据库
CREATE DATABASE lab_management DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 提示：执行完此脚本后，请立即执行 schema.sql










