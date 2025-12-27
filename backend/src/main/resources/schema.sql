-- ========================================
-- 智能实验室预约与设备管理系统 - 数据库设计
-- ========================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS lab_management DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE lab_management;

-- 先删除所有表（按照依赖关系的逆序）
DROP TABLE IF EXISTS `system_log`;
DROP TABLE IF EXISTS `maintenance_record`;
DROP TABLE IF EXISTS `equipment_reservation`;
DROP TABLE IF EXISTS `reservation`;
DROP TABLE IF EXISTS `course`;
DROP TABLE IF EXISTS `equipment`;
DROP TABLE IF EXISTS `laboratory`;
DROP TABLE IF EXISTS `user`;

-- ========================================
-- 1. 用户表 (user)
-- ========================================
CREATE TABLE `user` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '用户ID',
  `username` VARCHAR(50) NOT NULL COMMENT '用户名',
  `password` VARCHAR(255) NOT NULL COMMENT '密码（加密）',
  `name` VARCHAR(255) NOT NULL COMMENT '真实姓名',
  `role` VARCHAR(20) NOT NULL COMMENT '角色：ADMIN-管理员, TEACHER-教师, STUDENT-学生',
  `email` VARCHAR(100) COMMENT '邮箱',
  `phone` VARCHAR(20) COMMENT '手机号',
  `student_id` VARCHAR(50) COMMENT '学号/工号',
  `department` VARCHAR(100) COMMENT '院系',
  `status` TINYINT DEFAULT 1 COMMENT '状态：1-正常, 0-禁用',
  `avatar` VARCHAR(255) COMMENT '头像URL',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `deleted` TINYINT DEFAULT 0 COMMENT '逻辑删除：0-未删除, 1-已删除',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`),
  KEY `idx_role` (`role`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- ========================================
-- 2. 实验室表 (laboratory)
-- ========================================
CREATE TABLE `laboratory` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '实验室ID',
  `name` VARCHAR(255) NOT NULL COMMENT '实验室名称',
  `location` VARCHAR(200) NOT NULL COMMENT '位置',
  `building` VARCHAR(50) COMMENT '楼栋',
  `floor` INT COMMENT '楼层',
  `room_number` VARCHAR(20) COMMENT '房间号',
  `capacity` INT NOT NULL DEFAULT 30 COMMENT '容纳人数',
  `area` DECIMAL(10,2) COMMENT '面积（平方米）',
  `type` VARCHAR(50) COMMENT '实验室类型：计算机实验室、物理实验室等',
  `description` TEXT COMMENT '描述',
  `status` VARCHAR(20) NOT NULL DEFAULT 'IDLE' COMMENT '状态：IDLE-空闲, RESERVED-已预约, IN_USE-使用中, MAINTENANCE-维护中',
  `open_time` VARCHAR(500) COMMENT '开放时间（JSON格式）',
  `facilities` TEXT COMMENT '设施说明',
  `image_url` VARCHAR(255) COMMENT '实验室图片',
  `manager_id` BIGINT COMMENT '负责人ID',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `deleted` TINYINT DEFAULT 0 COMMENT '逻辑删除',
  PRIMARY KEY (`id`),
  KEY `idx_status` (`status`),
  KEY `idx_type` (`type`),
  KEY `idx_manager` (`manager_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='实验室表';

-- ========================================
-- 3. 设备表 (equipment)
-- ========================================
CREATE TABLE `equipment` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '设备ID',
  `name` VARCHAR(255) NOT NULL COMMENT '设备名称',
  `model` VARCHAR(100) COMMENT '型号',
  `lab_id` BIGINT NOT NULL COMMENT '所属实验室ID',
  `category` VARCHAR(50) COMMENT '设备类别',
  `serial_number` VARCHAR(100) COMMENT '序列号',
  `status` VARCHAR(20) NOT NULL DEFAULT 'IDLE' COMMENT '状态：IDLE-空闲, RESERVED-已预约, IN_USE-使用中, MAINTENANCE-维护中, SCRAPPED-报废',
  `purchase_date` DATE COMMENT '购买日期',
  `purchase_price` DECIMAL(10,2) COMMENT '购买价格',
  `warranty_period` INT COMMENT '保修期（月）',
  `description` TEXT COMMENT '设备描述',
  `image_url` VARCHAR(255) COMMENT '设备图片',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `deleted` TINYINT DEFAULT 0 COMMENT '逻辑删除',
  PRIMARY KEY (`id`),
  KEY `idx_lab_id` (`lab_id`),
  KEY `idx_status` (`status`),
  KEY `idx_category` (`category`),
  CONSTRAINT `fk_equipment_lab` FOREIGN KEY (`lab_id`) REFERENCES `laboratory` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='设备表';

-- ========================================
-- 4. 课程表 (course)
-- ========================================
CREATE TABLE `course` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '课程ID',
  `name` VARCHAR(255) NOT NULL COMMENT '课程名称',
  `code` VARCHAR(50) COMMENT '课程代码',
  `teacher_id` BIGINT NOT NULL COMMENT '授课教师ID',
  `lab_id` BIGINT COMMENT '默认实验室ID',
  `semester` VARCHAR(50) NOT NULL COMMENT '学期：如2024-2025-1',
  `student_count` INT DEFAULT 0 COMMENT '学生人数',
  `week_schedule` TEXT COMMENT '周课表（JSON格式）',
  `start_date` DATE COMMENT '开始日期',
  `end_date` DATE COMMENT '结束日期',
  `description` TEXT COMMENT '课程描述',
  `status` TINYINT DEFAULT 1 COMMENT '状态：1-进行中, 0-已结束',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `deleted` TINYINT DEFAULT 0 COMMENT '逻辑删除',
  PRIMARY KEY (`id`),
  KEY `idx_teacher_id` (`teacher_id`),
  KEY `idx_lab_id` (`lab_id`),
  KEY `idx_semester` (`semester`),
  CONSTRAINT `fk_course_teacher` FOREIGN KEY (`teacher_id`) REFERENCES `user` (`id`),
  CONSTRAINT `fk_course_lab` FOREIGN KEY (`lab_id`) REFERENCES `laboratory` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='课程表';

-- ========================================
-- 5. 预约表 (reservation)
-- ========================================
CREATE TABLE `reservation` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '预约ID',
  `user_id` BIGINT NOT NULL COMMENT '预约用户ID',
  `lab_id` BIGINT NOT NULL COMMENT '实验室ID',
  `type` VARCHAR(20) NOT NULL COMMENT '预约类型：SINGLE-单次, MULTIPLE-多次, COURSE-课程绑定',
  `start_time` DATETIME NOT NULL COMMENT '开始时间',
  `end_time` DATETIME NOT NULL COMMENT '结束时间',
  `purpose` VARCHAR(500) COMMENT '预约目的',
  `participant_count` INT DEFAULT 1 COMMENT '参与人数',
  `status` VARCHAR(20) NOT NULL DEFAULT 'PENDING' COMMENT '状态：PENDING-待审核, APPROVED-已通过, REJECTED-已拒绝, CANCELLED-已取消, COMPLETED-已完成',
  `course_id` BIGINT COMMENT '关联课程ID（课程预约时使用）',
  `parent_id` BIGINT COMMENT '父预约ID（多次预约时使用）',
  `approval_user_id` BIGINT COMMENT '审批人ID',
  `approval_time` DATETIME COMMENT '审批时间',
  `approval_remark` VARCHAR(500) COMMENT '审批备注',
  `check_in_time` DATETIME COMMENT '签到时间',
  `check_out_time` DATETIME COMMENT '签退时间',
  `remark` TEXT COMMENT '备注',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `deleted` TINYINT DEFAULT 0 COMMENT '逻辑删除',
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_lab_id` (`lab_id`),
  KEY `idx_status` (`status`),
  KEY `idx_type` (`type`),
  KEY `idx_time` (`start_time`, `end_time`),
  KEY `idx_course_id` (`course_id`),
  KEY `idx_parent_id` (`parent_id`),
  CONSTRAINT `fk_reservation_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`),
  CONSTRAINT `fk_reservation_lab` FOREIGN KEY (`lab_id`) REFERENCES `laboratory` (`id`),
  CONSTRAINT `fk_reservation_course` FOREIGN KEY (`course_id`) REFERENCES `course` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='预约表';

-- ========================================
-- 6. 设备预约表 (equipment_reservation)
-- ========================================
CREATE TABLE `equipment_reservation` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT 'ID',
  `reservation_id` BIGINT NOT NULL COMMENT '预约ID',
  `equipment_id` BIGINT NOT NULL COMMENT '设备ID',
  `quantity` INT DEFAULT 1 COMMENT '数量',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_reservation_id` (`reservation_id`),
  KEY `idx_equipment_id` (`equipment_id`),
  CONSTRAINT `fk_eq_res_reservation` FOREIGN KEY (`reservation_id`) REFERENCES `reservation` (`id`),
  CONSTRAINT `fk_eq_res_equipment` FOREIGN KEY (`equipment_id`) REFERENCES `equipment` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='设备预约关联表';

-- ========================================
-- 7. 维护记录表 (maintenance_record)
-- ========================================
CREATE TABLE `maintenance_record` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '记录ID',
  `resource_type` VARCHAR(20) NOT NULL COMMENT '资源类型：LAB-实验室, EQUIPMENT-设备',
  `resource_id` BIGINT NOT NULL COMMENT '资源ID',
  `type` VARCHAR(20) NOT NULL COMMENT '类型：MAINTENANCE-维护, REPAIR-维修, INSPECTION-检查',
  `start_time` DATETIME NOT NULL COMMENT '开始时间',
  `end_time` DATETIME COMMENT '结束时间',
  `reason` VARCHAR(500) NOT NULL COMMENT '原因',
  `description` TEXT COMMENT '详细描述',
  `cost` DECIMAL(10,2) COMMENT '费用',
  `operator_id` BIGINT NOT NULL COMMENT '操作人ID',
  `status` VARCHAR(20) DEFAULT 'IN_PROGRESS' COMMENT '状态：IN_PROGRESS-进行中, COMPLETED-已完成',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `deleted` TINYINT DEFAULT 0 COMMENT '逻辑删除',
  PRIMARY KEY (`id`),
  KEY `idx_resource` (`resource_type`, `resource_id`),
  KEY `idx_operator_id` (`operator_id`),
  KEY `idx_status` (`status`),
  CONSTRAINT `fk_maintenance_operator` FOREIGN KEY (`operator_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='维护记录表';

-- ========================================
-- 8. 系统日志表 (system_log)
-- ========================================
CREATE TABLE `system_log` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '日志ID',
  `user_id` BIGINT COMMENT '操作用户ID',
  `username` VARCHAR(50) COMMENT '用户名',
  `operation` VARCHAR(100) NOT NULL COMMENT '操作',
  `method` VARCHAR(200) COMMENT '方法名',
  `params` TEXT COMMENT '请求参数',
  `ip` VARCHAR(50) COMMENT 'IP地址',
  `result` VARCHAR(20) COMMENT '结果：SUCCESS-成功, FAIL-失败',
  `error_msg` TEXT COMMENT '错误信息',
  `execution_time` INT COMMENT '执行时间（毫秒）',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统日志表';

-- ========================================
-- 初始化数据
-- ========================================
-- 注意：密码会在应用启动时自动加密（通过 DataInitializer）
-- 你可以直接使用明文密码，系统会自动检测并加密

-- 插入管理员账号（密码：admin123）
INSERT INTO `user` (`username`, `password`, `name`, `role`, `email`, `phone`, `status`) VALUES
('admin', 'admin123', '系统管理员', 'ADMIN', 'admin@lab.com', '13800138000', 1);

-- 插入测试教师账号（密码：teacher123）
INSERT INTO `user` (`username`, `password`, `name`, `role`, `email`, `phone`, `student_id`, `department`, `status`) VALUES
('teacher1', 'teacher123', '张老师', 'TEACHER', 'teacher1@lab.com', '13800138001', 'T001', '计算机学院', 1);

INSERT INTO `user` (`username`, `password`, `name`, `role`, `email`, `phone`, `student_id`, `department`, `status`) VALUES
('teacher2', 'teacher123', '李老师', 'TEACHER', 'teacher2@lab.com', '13800138002', 'T002', '物理学院', 1);

-- 插入测试学生账号（密码：student123）
INSERT INTO `user` (`username`, `password`, `name`, `role`, `email`, `phone`, `student_id`, `department`, `status`) VALUES
('student1', 'student123', '王同学', 'STUDENT', 'student1@lab.com', '13800138011', '2021001', '计算机学院', 1);

INSERT INTO `user` (`username`, `password`, `name`, `role`, `email`, `phone`, `student_id`, `department`, `status`) VALUES
('student2', 'student123', '刘同学', 'STUDENT', 'student2@lab.com', '13800138012', '2021002', '计算机学院', 1);

-- 插入测试实验室
INSERT INTO `laboratory` (`name`, `location`, `building`, `floor`, `room_number`, `capacity`, `area`, `type`, `description`, `status`) VALUES
('计算机实验室A', '教学楼A栋3楼301', 'A栋', 3, '301', 50, 120.00, '计算机实验室', '配备50台高性能计算机', 'IDLE');

INSERT INTO `laboratory` (`name`, `location`, `building`, `floor`, `room_number`, `capacity`, `area`, `type`, `description`, `status`) VALUES
('计算机实验室B', '教学楼A栋3楼302', 'A栋', 3, '302', 40, 100.00, '计算机实验室', '配备40台计算机', 'IDLE');

INSERT INTO `laboratory` (`name`, `location`, `building`, `floor`, `room_number`, `capacity`, `area`, `type`, `description`, `status`) VALUES
('物理实验室', '实验楼B栋2楼201', 'B栋', 2, '201', 30, 150.00, '物理实验室', '配备物理实验设备', 'IDLE');

INSERT INTO `laboratory` (`name`, `location`, `building`, `floor`, `room_number`, `capacity`, `area`, `type`, `description`, `status`) VALUES
('化学实验室', '实验楼B栋2楼202', 'B栋', 2, '202', 30, 150.00, '化学实验室', '配备化学实验设备', 'IDLE');

INSERT INTO `laboratory` (`name`, `location`, `building`, `floor`, `room_number`, `capacity`, `area`, `type`, `description`, `status`) VALUES
('电子实验室', '实验楼C栋1楼101', 'C栋', 1, '101', 35, 110.00, '电子实验室', '配备电子设备', 'IDLE');

-- 插入测试设备
INSERT INTO `equipment` (`name`, `model`, `lab_id`, `category`, `serial_number`, `status`, `purchase_date`, `description`) VALUES
('高性能计算机', 'Dell OptiPlex 7090', 1, '计算机', 'PC001', 'IDLE', '2023-09-01', 'i7处理器，16GB内存，512GB SSD');

INSERT INTO `equipment` (`name`, `model`, `lab_id`, `category`, `serial_number`, `status`, `purchase_date`, `description`) VALUES
('投影仪', 'Epson CB-X05', 1, '多媒体设备', 'PJ001', 'IDLE', '2023-09-01', '高清投影仪');

INSERT INTO `equipment` (`name`, `model`, `lab_id`, `category`, `serial_number`, `status`, `purchase_date`, `description`) VALUES
('示波器', 'Tektronix TBS2000', 5, '测量仪器', 'OSC001', 'IDLE', '2023-08-15', '数字示波器');

INSERT INTO `equipment` (`name`, `model`, `lab_id`, `category`, `serial_number`, `status`, `purchase_date`, `description`) VALUES
('信号发生器', 'Agilent 33220A', 5, '测量仪器', 'SG001', 'IDLE', '2023-08-15', '函数信号发生器');

INSERT INTO `equipment` (`name`, `model`, `lab_id`, `category`, `serial_number`, `status`, `purchase_date`, `description`) VALUES
('显微镜', 'Olympus CX23', 3, '光学仪器', 'MIC001', 'IDLE', '2023-07-20', '生物显微镜');

-- ========================================
-- 创建视图：实验室使用统计
-- ========================================
CREATE OR REPLACE VIEW `v_lab_usage_stats` AS
SELECT 
    l.id AS lab_id,
    l.name AS lab_name,
    COUNT(r.id) AS total_reservations,
    SUM(CASE WHEN r.status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed_reservations,
    SUM(CASE WHEN r.status = 'APPROVED' THEN 1 ELSE 0 END) AS approved_reservations,
    SUM(CASE WHEN r.status = 'PENDING' THEN 1 ELSE 0 END) AS pending_reservations
FROM laboratory l
LEFT JOIN reservation r ON l.id = r.lab_id AND r.deleted = 0
WHERE l.deleted = 0
GROUP BY l.id, l.name;

-- ========================================
-- 数据库设计完成
-- ========================================

