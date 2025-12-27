-- ========================================
-- 密码更新脚本
-- ========================================
-- 使用说明：
-- 1. 先运行 schema.sql 创建数据库和表
-- 2. 启动后端服务
-- 3. 访问 http://localhost:8080/api/test/generate-password?password=admin123 获取加密密码
-- 4. 将生成的密码替换下面的 'REPLACE_WITH_ENCRYPTED_PASSWORD'
-- 5. 运行此脚本更新密码

USE lab_management;

-- 更新 admin 密码（密码：admin123）
-- 请先访问 /test/generate-password?password=admin123 获取加密密码
UPDATE `user` SET `password` = 'REPLACE_WITH_ENCRYPTED_PASSWORD' WHERE `username` = 'admin';

-- 更新 teacher 密码（密码：teacher123）
-- 请先访问 /test/generate-password?password=teacher123 获取加密密码
UPDATE `user` SET `password` = 'REPLACE_WITH_ENCRYPTED_PASSWORD' WHERE `username` = 'teacher1';
UPDATE `user` SET `password` = 'REPLACE_WITH_ENCRYPTED_PASSWORD' WHERE `username` = 'teacher2';

-- 更新 student 密码（密码：student123）
-- 请先访问 /test/generate-password?password=student123 获取加密密码
UPDATE `user` SET `password` = 'REPLACE_WITH_ENCRYPTED_PASSWORD' WHERE `username` = 'student1';
UPDATE `user` SET `password` = 'REPLACE_WITH_ENCRYPTED_PASSWORD' WHERE `username` = 'student2';

-- 验证更新
SELECT username, LEFT(password, 30) as password_preview, role FROM `user`;

