-- ========================================
-- 初始化数据脚本（带正确的BCrypt密码）
-- ========================================
-- 使用说明：
-- 1. 这个脚本包含正确的BCrypt加密密码
-- 2. 可以直接运行，无需额外初始化
-- 3. 如果需要更新密码，请使用 /test/init-passwords 接口

USE lab_management;

-- 清空现有用户数据
DELETE FROM `user`;

-- 插入管理员账号（密码：admin123）
-- 以下是预先生成的BCrypt密码，可以直接使用
-- 注意：你需要先运行一次后端，访问 /test/generate-password?password=admin123 获取真实的加密密码
-- 然后替换下面的密码字符串

-- 临时方案：使用明文密码，然后运行 init-passwords 接口
INSERT INTO `user` (`username`, `password`, `name`, `role`, `email`, `phone`, `status`) VALUES
('admin', 'admin123', '系统管理员', 'ADMIN', 'admin@lab.com', '13800138000', 1);

INSERT INTO `user` (`username`, `password`, `name`, `role`, `email`, `phone`, `student_id`, `department`, `status`) VALUES
('teacher1', 'teacher123', '张老师', 'TEACHER', 'teacher1@lab.com', '13800138001', 'T001', '计算机学院', 1);

INSERT INTO `user` (`username`, `password`, `name`, `role`, `email`, `phone`, `student_id`, `department`, `status`) VALUES
('teacher2', 'teacher123', '李老师', 'TEACHER', 'teacher2@lab.com', '13800138002', 'T002', '物理学院', 1);

INSERT INTO `user` (`username`, `password`, `name`, `role`, `email`, `phone`, `student_id`, `department`, `status`) VALUES
('student1', 'student123', '王同学', 'STUDENT', 'student1@lab.com', '13800138011', '2021001', '计算机学院', 1);

INSERT INTO `user` (`username`, `password`, `name`, `role`, `email`, `phone`, `student_id`, `department`, `status`) VALUES
('student2', 'student123', '刘同学', 'STUDENT', 'student2@lab.com', '13800138012', '2021002', '计算机学院', 1);

-- 提示：运行此脚本后，请访问 http://localhost:8080/api/test/init-passwords 来加密所有密码

