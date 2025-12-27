-- ========================================
-- 插入设备测试数据
-- ========================================
-- 使用方法：在MySQL命令行中执行 source 插入设备测试数据.sql;
-- ========================================

SET NAMES utf8mb4;
USE lab_management;

-- ========================================
-- 1. 获取实验室ID（假设至少有一个实验室）
-- ========================================
SET @lab1_id = (SELECT id FROM `laboratory` WHERE deleted = 0 LIMIT 1);
SET @lab2_id = (SELECT id FROM `laboratory` WHERE deleted = 0 LIMIT 1 OFFSET 1);
SET @lab3_id = (SELECT id FROM `laboratory` WHERE deleted = 0 LIMIT 1 OFFSET 2);

-- 如果实验室不存在，先创建一个
INSERT INTO `laboratory` (`name`, `location`, `capacity`, `type`, `description`, `status`) 
SELECT '计算机实验室A', '教学楼A栋3楼301', 50, '计算机实验室', '配备50台高性能计算机', 'IDLE'
WHERE NOT EXISTS (SELECT 1 FROM `laboratory` WHERE deleted = 0 LIMIT 1);

-- 重新获取实验室ID
SET @lab1_id = (SELECT id FROM `laboratory` WHERE deleted = 0 LIMIT 1);
SET @lab2_id = (SELECT id FROM `laboratory` WHERE deleted = 0 LIMIT 1 OFFSET 1);
SET @lab3_id = (SELECT id FROM `laboratory` WHERE deleted = 0 LIMIT 1 OFFSET 2);

-- ========================================
-- 2. 插入设备数据（如果不存在）
-- ========================================

-- 计算机实验室设备
INSERT INTO `equipment` (`name`, `model`, `lab_id`, `category`, `serial_number`, `status`, `purchase_date`, `purchase_price`, `warranty_period`, `description`) 
SELECT '高性能计算机', 'Dell OptiPlex 7090', @lab1_id, '计算机', 'PC-001', 'IDLE', '2023-01-15', 8000.00, 36, 'Intel i7处理器，16GB内存，512GB SSD'
WHERE @lab1_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM `equipment` WHERE name = '高性能计算机' AND deleted = 0);

INSERT INTO `equipment` (`name`, `model`, `lab_id`, `category`, `serial_number`, `status`, `purchase_date`, `purchase_price`, `warranty_period`, `description`) 
SELECT '服务器', 'Dell PowerEdge R740', @lab1_id, '服务器', 'SRV-001', 'IDLE', '2023-02-20', 25000.00, 60, '双路Xeon处理器，64GB内存，2TB存储'
WHERE @lab1_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM `equipment` WHERE name = '服务器' AND deleted = 0);

INSERT INTO `equipment` (`name`, `model`, `lab_id`, `category`, `serial_number`, `status`, `purchase_date`, `purchase_price`, `warranty_period`, `description`) 
SELECT '网络交换机', 'Cisco Catalyst 2960', @lab1_id, '网络设备', 'NET-001', 'IDLE', '2023-03-10', 5000.00, 36, '24端口千兆交换机'
WHERE @lab1_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM `equipment` WHERE name = '网络交换机' AND deleted = 0);

-- 物理实验室设备（如果lab2存在）
INSERT INTO `equipment` (`name`, `model`, `lab_id`, `category`, `serial_number`, `status`, `purchase_date`, `purchase_price`, `warranty_period`, `description`) 
SELECT '示波器', 'Tektronix TBS2000', @lab2_id, '测量仪器', 'OSC-001', 'IN_USE', '2022-06-20', 12000.00, 24, '数字存储示波器，200MHz带宽'
WHERE @lab2_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM `equipment` WHERE name = '示波器' AND deleted = 0);

INSERT INTO `equipment` (`name`, `model`, `lab_id`, `category`, `serial_number`, `status`, `purchase_date`, `purchase_price`, `warranty_period`, `description`) 
SELECT '信号发生器', 'Keysight 33500B', @lab2_id, '信号源', 'SIG-001', 'IDLE', '2022-07-15', 15000.00, 36, '双通道函数/任意波形发生器'
WHERE @lab2_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM `equipment` WHERE name = '信号发生器' AND deleted = 0);

INSERT INTO `equipment` (`name`, `model`, `lab_id`, `category`, `serial_number`, `status`, `purchase_date`, `purchase_price`, `warranty_period`, `description`) 
SELECT '万用表', 'Fluke 87V', @lab2_id, '测量仪器', 'MM-001', 'IDLE', '2022-08-01', 800.00, 12, '数字万用表，真有效值测量'
WHERE @lab2_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM `equipment` WHERE name = '万用表' AND deleted = 0);

-- 化学实验室设备（如果lab3存在）
INSERT INTO `equipment` (`name`, `model`, `lab_id`, `category`, `serial_number`, `status`, `purchase_date`, `purchase_price`, `warranty_period`, `description`) 
SELECT '离心机', 'Eppendorf 5424R', @lab3_id, '实验设备', 'CEN-001', 'MAINTENANCE', '2023-03-10', 18000.00, 24, '冷冻离心机，最大转速15000rpm'
WHERE @lab3_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM `equipment` WHERE name = '离心机' AND deleted = 0);

INSERT INTO `equipment` (`name`, `model`, `lab_id`, `category`, `serial_number`, `status`, `purchase_date`, `purchase_price`, `warranty_period`, `description`) 
SELECT '电子天平', 'Sartorius BSA224S', @lab3_id, '测量仪器', 'BAL-001', 'IDLE', '2023-04-05', 3500.00, 12, '分析天平，精度0.1mg'
WHERE @lab3_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM `equipment` WHERE name = '电子天平' AND deleted = 0);

-- 如果lab2和lab3不存在，将设备添加到lab1
INSERT INTO `equipment` (`name`, `model`, `lab_id`, `category`, `serial_number`, `status`, `purchase_date`, `purchase_price`, `warranty_period`, `description`) 
SELECT '示波器', 'Tektronix TBS2000', @lab1_id, '测量仪器', 'OSC-001', 'IN_USE', '2022-06-20', 12000.00, 24, '数字存储示波器，200MHz带宽'
WHERE @lab1_id IS NOT NULL AND @lab2_id IS NULL AND NOT EXISTS (SELECT 1 FROM `equipment` WHERE name = '示波器' AND deleted = 0);

INSERT INTO `equipment` (`name`, `model`, `lab_id`, `category`, `serial_number`, `status`, `purchase_date`, `purchase_price`, `warranty_period`, `description`) 
SELECT '离心机', 'Eppendorf 5424R', @lab1_id, '实验设备', 'CEN-001', 'MAINTENANCE', '2023-03-10', 18000.00, 24, '冷冻离心机，最大转速15000rpm'
WHERE @lab1_id IS NOT NULL AND @lab3_id IS NULL AND NOT EXISTS (SELECT 1 FROM `equipment` WHERE name = '离心机' AND deleted = 0);

-- ========================================
-- 3. 验证数据
-- ========================================

SELECT '设备数据统计' AS info;
SELECT COUNT(*) AS total_equipment FROM `equipment` WHERE deleted = 0;

SELECT '按状态统计' AS info;
SELECT status, COUNT(*) AS count FROM `equipment` WHERE deleted = 0 GROUP BY status;

SELECT '按实验室统计' AS info;
SELECT l.name AS lab_name, COUNT(e.id) AS equipment_count 
FROM `laboratory` l 
LEFT JOIN `equipment` e ON l.id = e.lab_id AND e.deleted = 0 
WHERE l.deleted = 0 
GROUP BY l.id, l.name;

SELECT '设备列表' AS info;
SELECT e.id, e.name, e.model, l.name AS lab_name, e.status, e.purchase_date 
FROM `equipment` e 
LEFT JOIN `laboratory` l ON e.lab_id = l.id 
WHERE e.deleted = 0 
ORDER BY e.id;

