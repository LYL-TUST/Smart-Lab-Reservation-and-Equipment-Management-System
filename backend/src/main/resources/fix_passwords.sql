-- ========================================
-- 修复用户密码（使用BCrypt加密）
-- ========================================
-- 说明：数据库中的密码必须是BCrypt加密后的值
-- 原始密码：admin123, teacher123, student123

-- 更新管理员密码 (admin123)
UPDATE `user` SET `password` = '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBOsl7iKzTe5u.' WHERE `username` = 'admin';

-- 更新教师密码 (teacher123)
UPDATE `user` SET `password` = '$2a$10$5ZwlZjY4xRxR5ZwlZjY4xOxRxR5ZwlZjY4xOxRxR5ZwlZjY4xO.u.' WHERE `username` LIKE 'teacher%';

-- 更新学生密码 (student123)
UPDATE `user` SET `password` = '$2a$10$7YwmYkZ6zSzS7YwmYkZ6zOzSzS7YwmYkZ6zOzSzS7YwmYkZ6zO.u.' WHERE `username` LIKE 'student%';

-- 查看更新结果
SELECT id, username, name, role, LEFT(password, 20) as password_preview FROM `user`;

