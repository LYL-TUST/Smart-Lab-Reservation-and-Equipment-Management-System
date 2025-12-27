-- ========================================
-- 确保数据库有测试数据（用户和课程）
-- ========================================
-- 使用方法：在MySQL命令行中执行 source 确保数据库有测试数据.sql;
-- ========================================

SET NAMES utf8mb4;
USE lab_management;

-- ========================================
-- 1. 检查并插入用户数据
-- ========================================

-- 检查是否有管理员
SELECT COUNT(*) AS admin_count FROM `user` WHERE role = 'ADMIN' AND deleted = 0;
-- 如果没有管理员，插入一个
INSERT INTO `user` (`username`, `password`, `name`, `role`, `email`, `phone`, `status`) 
SELECT 'admin', '$2a$10$8.VxkAkGCiTpefHnjANMWOYHJfJYwKyiwX4dB4veEhj33mMB4VTGG', '系统管理员', 'ADMIN', 'admin@lab.com', '13800138000', 1
WHERE NOT EXISTS (SELECT 1 FROM `user` WHERE username = 'admin' AND deleted = 0);

-- 检查是否有教师
SELECT COUNT(*) AS teacher_count FROM `user` WHERE role = 'TEACHER' AND deleted = 0;
-- 如果没有教师，插入两个测试教师
INSERT INTO `user` (`username`, `password`, `name`, `role`, `email`, `phone`, `student_id`, `department`, `status`) 
SELECT 'teacher1', '$2a$10$8.VxkAkGCiTpefHnjANMWOYHJfJYwKyiwX4dB4veEhj33mMB4VTGG', '张老师', 'TEACHER', 'teacher1@lab.com', '13800138001', 'T001', '计算机学院', 1
WHERE NOT EXISTS (SELECT 1 FROM `user` WHERE username = 'teacher1' AND deleted = 0);

INSERT INTO `user` (`username`, `password`, `name`, `role`, `email`, `phone`, `student_id`, `department`, `status`) 
SELECT 'teacher2', '$2a$10$8.VxkAkGCiTpefHnjANMWOYHJfJYwKyiwX4dB4veEhj33mMB4VTGG', '李老师', 'TEACHER', 'teacher2@lab.com', '13800138002', 'T002', '物理学院', 1
WHERE NOT EXISTS (SELECT 1 FROM `user` WHERE username = 'teacher2' AND deleted = 0);

-- 检查是否有学生
SELECT COUNT(*) AS student_count FROM `user` WHERE role = 'STUDENT' AND deleted = 0;
-- 如果没有学生，插入两个测试学生
INSERT INTO `user` (`username`, `password`, `name`, `role`, `email`, `phone`, `student_id`, `department`, `status`) 
SELECT 'student1', '$2a$10$8.VxkAkGCiTpefHnjANMWOYHJfJYwKyiwX4dB4veEhj33mMB4VTGG', '王同学', 'STUDENT', 'student1@lab.com', '13800138011', '2021001', '计算机学院', 1
WHERE NOT EXISTS (SELECT 1 FROM `user` WHERE username = 'student1' AND deleted = 0);

INSERT INTO `user` (`username`, `password`, `name`, `role`, `email`, `phone`, `student_id`, `department`, `status`) 
SELECT 'student2', '$2a$10$8.VxkAkGCiTpefHnjANMWOYHJfJYwKyiwX4dB4veEhj33mMB4VTGG', '刘同学', 'STUDENT', 'student2@lab.com', '13800138012', '2021002', '计算机学院', 1
WHERE NOT EXISTS (SELECT 1 FROM `user` WHERE username = 'student2' AND deleted = 0);

-- ========================================
-- 2. 检查并插入课程数据
-- ========================================

-- 获取教师ID（假设teacher1的ID是2，teacher2的ID是3）
SET @teacher1_id = (SELECT id FROM `user` WHERE username = 'teacher1' AND deleted = 0 LIMIT 1);
SET @teacher2_id = (SELECT id FROM `user` WHERE username = 'teacher2' AND deleted = 0 LIMIT 1);

-- 获取实验室ID（假设至少有一个实验室）
SET @lab1_id = (SELECT id FROM `laboratory` WHERE deleted = 0 LIMIT 1);
SET @lab2_id = (SELECT id FROM `laboratory` WHERE deleted = 0 LIMIT 1 OFFSET 1);
SET @lab3_id = (SELECT id FROM `laboratory` WHERE deleted = 0 LIMIT 1 OFFSET 2);

-- 检查是否有课程
SELECT COUNT(*) AS course_count FROM `course` WHERE deleted = 0;

-- 如果没有课程且教师和实验室都存在，插入测试课程
INSERT INTO `course` (`name`, `code`, `teacher_id`, `lab_id`, `semester`, `student_count`, `description`, `status`, `start_date`, `end_date`, `week_schedule`) 
SELECT 'Java程序设计', 'CS101', @teacher1_id, @lab1_id, '2024-2025学年第一学期', 45, '面向对象程序设计基础课程，学习Java语言特性和编程实践', 1, '2024-09-01', '2025-01-15', '{"周一":["08:00-09:40"],"周三":["10:00-11:40"]}'
WHERE @teacher1_id IS NOT NULL AND @lab1_id IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM `course` WHERE code = 'CS101' AND deleted = 0);

INSERT INTO `course` (`name`, `code`, `teacher_id`, `lab_id`, `semester`, `student_count`, `description`, `status`, `start_date`, `end_date`, `week_schedule`) 
SELECT '数据结构与算法', 'CS102', @teacher1_id, @lab1_id, '2024-2025学年第一学期', 50, '计算机专业核心课程，学习常用数据结构和算法设计', 1, '2024-09-01', '2025-01-15', '{"周二":["08:00-09:40"],"周四":["10:00-11:40"]}'
WHERE @teacher1_id IS NOT NULL AND @lab1_id IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM `course` WHERE code = 'CS102' AND deleted = 0);

INSERT INTO `course` (`name`, `code`, `teacher_id`, `lab_id`, `semester`, `student_count`, `description`, `status`, `start_date`, `end_date`, `week_schedule`) 
SELECT '大学物理实验', 'PHY201', @teacher2_id, @lab2_id, '2024-2025学年第一学期', 40, '物理实验基础课程，进行各类物理实验操作', 1, '2024-09-01', '2025-01-15', '{"周二":["14:00-17:40"],"周四":["14:00-17:40"]}'
WHERE @teacher2_id IS NOT NULL AND @lab2_id IS NOT NULL 
  AND NOT EXISTS (SELECT 1 FROM `course` WHERE code = 'PHY201' AND deleted = 0);

-- ========================================
-- 3. 验证数据
-- ========================================

SELECT '用户数据统计' AS info;
SELECT role, COUNT(*) AS count FROM `user` WHERE deleted = 0 GROUP BY role;

SELECT '课程数据统计' AS info;
SELECT COUNT(*) AS course_count FROM `course` WHERE deleted = 0;

SELECT '教师列表' AS info;
SELECT id, username, name, role FROM `user` WHERE role = 'TEACHER' AND deleted = 0;

SELECT '课程列表' AS info;
SELECT id, name, code, teacher_id FROM `course` WHERE deleted = 0 LIMIT 10;

