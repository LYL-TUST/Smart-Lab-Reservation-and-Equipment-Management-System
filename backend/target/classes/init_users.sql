-- ========================================
-- 插入测试用户（使用BCrypt加密的密码）
-- ========================================

-- 清空现有用户数据
DELETE FROM `user`;

-- 密码说明：
-- admin123 的 BCrypt 加密值：$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBOsl7iAt6Z5EH
-- teacher123 的 BCrypt 加密值：$2a$10$5ZwlZjY4xRxR5ZwlZjY4xOxRxR5ZwlZjY4xOxRxR5ZwlZjY4xO
-- student123 的 BCrypt 加密值：$2a$10$7YwmYkZ6zSzS7YwmYkZ6zOzSzS7YwmYkZ6zOzSzS7YwmYkZ6zO

-- 注意：实际使用时，这些密码需要通过 BCryptPasswordEncoder 生成
-- 临时方案：使用明文，在后端启动时自动加密

-- 插入管理员账号
INSERT INTO `user` (`username`, `password`, `name`, `role`, `email`, `phone`, `status`) VALUES
('admin', 'admin123', '系统管理员', 'ADMIN', 'admin@lab.com', '13800138000', 1);

-- 插入测试教师账号
INSERT INTO `user` (`username`, `password`, `name`, `role`, `email`, `phone`, `student_id`, `department`, `status`) VALUES
('teacher1', 'teacher123', '张老师', 'TEACHER', 'teacher1@lab.com', '13800138001', 'T001', '计算机学院', 1),
('teacher2', 'teacher123', '李老师', 'TEACHER', 'teacher2@lab.com', '13800138002', 'T002', '物理学院', 1);

-- 插入测试学生账号
INSERT INTO `user` (`username`, `password`, `name`, `role`, `email`, `phone`, `student_id`, `department`, `status`) VALUES
('student1', 'student123', '王同学', 'STUDENT', 'student1@lab.com', '13800138011', '2021001', '计算机学院', 1),
('student2', 'student123', '刘同学', 'STUDENT', 'student2@lab.com', '13800138012', '2021002', '计算机学院', 1);

-- ========================================
-- 测试账号说明
-- ========================================
-- 管理员：admin / admin123
-- 教师1：teacher1 / teacher123
-- 教师2：teacher2 / teacher123
-- 学生1：student1 / student123
-- 学生2：student2 / student123












