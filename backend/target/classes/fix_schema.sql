-- ========================================
-- 修复脚本：强制删除并重建数据库
-- ========================================

-- 方案1：完全删除数据库并重建
DROP DATABASE IF EXISTS lab_management;
CREATE DATABASE lab_management DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 然后使用 schema.sql 重新导入

