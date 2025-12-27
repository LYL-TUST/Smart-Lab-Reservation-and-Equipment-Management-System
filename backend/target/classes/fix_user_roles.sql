-- 修复用户角色问题
-- 说明：系统支持三种角色 ADMIN（管理员）、TEACHER（教师）、STUDENT（学生）

-- 1. 查看当前所有用户的角色
SELECT id, username, name, role, email FROM user WHERE deleted = 0;

-- 2. 确保 admin 用户的角色是 ADMIN
UPDATE user 
SET role = 'ADMIN' 
WHERE username = 'admin' 
  AND deleted = 0;

-- 3. 将其他用户设置为合适的角色（根据实际情况修改）
-- 如果不确定，可以先都设置为 STUDENT，然后手动调整教师账号
UPDATE user 
SET role = 'STUDENT' 
WHERE username != 'admin' 
  AND deleted = 0
  AND (role IS NULL OR role = '' OR role = 'ADMIN');

-- 4. 验证修复结果
SELECT id, username, name, role, email FROM user WHERE deleted = 0 ORDER BY role, id;

-- 5. 统计各角色用户数量
SELECT role, COUNT(*) as count 
FROM user 
WHERE deleted = 0 
GROUP BY role;

-- 注意：
-- 如果需要将某些用户设置为教师，请手动执行：
-- UPDATE user SET role = 'TEACHER' WHERE username = '教师用户名' AND deleted = 0;

