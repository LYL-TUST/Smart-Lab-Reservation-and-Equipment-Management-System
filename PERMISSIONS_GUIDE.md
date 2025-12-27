# 权限系统使用指南

## 概述

本系统实现了完整的基于角色的访问控制（RBAC），三个角色（管理员、教师、学生）拥有不同的权限。

## 角色权限说明

### 1. 管理员 (ADMIN)
拥有系统所有权限，包括：
- ✅ 查看所有数据
- ✅ 管理用户
- ✅ 管理实验室（增删改查）
- ✅ 管理设备（增删改查）
- ✅ 管理课程（增删改查）
- ✅ 审批预约
- ✅ 管理所有预约

### 2. 教师 (TEACHER)
拥有教学相关权限，包括：
- ✅ 查看实验室、设备、课程
- ✅ 编辑实验室信息
- ✅ 维护设备
- ✅ 创建、编辑、删除课程
- ✅ 审批学生预约
- ✅ 创建和管理自己的预约
- ❌ 不能管理用户
- ❌ 不能删除实验室和设备

### 3. 学生 (STUDENT)
拥有基本使用权限，包括：
- ✅ 查看实验室、设备、课程
- ✅ 创建预约
- ✅ 编辑和取消自己的预约
- ❌ 不能审批预约
- ❌ 不能管理实验室、设备、课程
- ❌ 不能管理用户

## 权限控制实现

### 1. 路由级别权限控制

在 `router/index.js` 中配置：

```javascript
{
  path: 'users',
  name: 'Users',
  component: () => import('../views/Users.vue'),
  meta: { 
    title: '用户管理', 
    icon: 'User',
    roles: [ROLES.ADMIN],  // 只有管理员可以访问
    permissions: [PERMISSIONS.USER_MANAGE]
  }
}
```

### 2. 页面元素级别权限控制

使用 `v-permission` 指令：

```vue
<!-- 单个权限 -->
<el-button v-permission="'lab:create'" type="primary">
  添加实验室
</el-button>

<!-- 多个权限（任一） -->
<el-button v-permission="['lab:edit', 'lab:create']" type="primary">
  操作
</el-button>

<!-- 多个权限（全部） -->
<el-button v-permission.all="['lab:edit', 'lab:delete']" type="danger">
  删除
</el-button>
```

使用 `v-role` 指令：

```vue
<!-- 单个角色 -->
<div v-role="'ADMIN'">管理员专属内容</div>

<!-- 多个角色 -->
<div v-role="['ADMIN', 'TEACHER']">管理员和教师可见</div>
```

### 3. 代码级别权限控制

在组件中使用权限判断函数：

```javascript
import { hasPermission, ROLES } from '../config/permissions'
import { useUserStore } from '../stores/user'

const userStore = useUserStore()
const userRole = computed(() => userStore.userInfo?.role)

// 判断是否有权限
const canEdit = computed(() => {
  return hasPermission(userRole.value, 'lab:edit')
})

// 判断是否是管理员
const isAdmin = computed(() => {
  return userRole.value === ROLES.ADMIN
})
```

## 各页面权限配置

### 预约管理 (Reservations.vue)

| 功能 | 管理员 | 教师 | 学生 |
|------|--------|------|------|
| 查看预约 | ✅ | ✅ | ✅ |
| 新建预约 | ✅ | ✅ | ✅ |
| 编辑预约 | ✅ | ✅ | ✅ (仅自己的) |
| 取消预约 | ✅ | ✅ | ✅ (仅自己的) |
| 审批预约 | ✅ | ✅ | ❌ |

### 实验室管理 (Laboratories.vue)

| 功能 | 管理员 | 教师 | 学生 |
|------|--------|------|------|
| 查看实验室 | ✅ | ✅ | ✅ |
| 添加实验室 | ✅ | ❌ | ❌ |
| 编辑实验室 | ✅ | ✅ | ❌ |
| 删除实验室 | ✅ | ❌ | ❌ |

### 设备管理 (Equipment.vue)

| 功能 | 管理员 | 教师 | 学生 |
|------|--------|------|------|
| 查看设备 | ✅ | ✅ | ✅ |
| 添加设备 | ✅ | ❌ | ❌ |
| 编辑设备 | ✅ | ✅ | ❌ |
| 删除设备 | ✅ | ❌ | ❌ |
| 设备维护 | ✅ | ✅ | ❌ |

### 课程管理 (Courses.vue)

| 功能 | 管理员 | 教师 | 学生 |
|------|--------|------|------|
| 查看课程 | ✅ | ✅ | ✅ |
| 添加课程 | ✅ | ✅ | ❌ |
| 编辑课程 | ✅ | ✅ | ❌ |
| 删除课程 | ✅ | ✅ | ❌ |

### 用户管理 (Users.vue)

| 功能 | 管理员 | 教师 | 学生 |
|------|--------|------|------|
| 访问页面 | ✅ | ❌ | ❌ |
| 查看用户 | ✅ | ❌ | ❌ |
| 添加用户 | ✅ | ❌ | ❌ |
| 编辑用户 | ✅ | ❌ | ❌ |
| 删除用户 | ✅ | ❌ | ❌ |

### 仪表盘 (Dashboard.vue)

| 功能 | 管理员 | 教师 | 学生 |
|------|--------|------|------|
| 查看统计 | ✅ | ✅ | ✅ |
| 查看活跃用户 | ✅ | ❌ | ❌ |

## 测试权限

### 测试账号

1. **管理员账号**
   - 用户名: admin
   - 密码: admin123
   - 角色: ADMIN

2. **教师账号**
   - 用户名: teacher
   - 密码: teacher123
   - 角色: TEACHER

3. **学生账号**
   - 用户名: student
   - 密码: student123
   - 角色: STUDENT

### 测试步骤

1. **测试路由权限**
   - 使用学生账号登录
   - 尝试访问 `/users` 路径
   - 应该被重定向到 403 页面

2. **测试按钮权限**
   - 使用学生账号登录
   - 进入实验室管理页面
   - "添加实验室"按钮应该不可见
   - "编辑"和"删除"按钮应该不可见

3. **测试预约权限**
   - 使用学生账号登录
   - 进入预约管理页面
   - 可以看到"新建预约"按钮
   - 只能编辑和取消自己的预约
   - 看不到"审批"按钮

4. **测试教师权限**
   - 使用教师账号登录
   - 可以看到"审批"按钮
   - 可以编辑实验室和设备
   - 可以管理课程
   - 看不到用户管理菜单

5. **测试管理员权限**
   - 使用管理员账号登录
   - 可以看到所有菜单
   - 可以执行所有操作

## 权限配置文件

所有权限配置在 `src/config/permissions.js` 中定义：

```javascript
// 角色定义
export const ROLES = {
    ADMIN: 'ADMIN',
    TEACHER: 'TEACHER',
    STUDENT: 'STUDENT'
}

// 权限定义
export const PERMISSIONS = {
    DASHBOARD_VIEW: 'dashboard:view',
    RESERVATION_VIEW: 'reservation:view',
    RESERVATION_CREATE: 'reservation:create',
    // ... 更多权限
}

// 角色权限映射
export const ROLE_PERMISSIONS = {
    [ROLES.ADMIN]: [/* 所有权限 */],
    [ROLES.TEACHER]: [/* 教师权限 */],
    [ROLES.STUDENT]: [/* 学生权限 */]
}
```

## 添加新权限

1. 在 `PERMISSIONS` 对象中定义新权限
2. 在 `ROLE_PERMISSIONS` 中为相应角色添加权限
3. 在页面中使用 `v-permission` 指令控制元素显示
4. 在路由配置中添加权限要求（如需要）

## 注意事项

1. **前端权限控制只是UI层面的控制**，真正的权限验证必须在后端进行
2. 权限指令会直接移除DOM元素，而不是隐藏
3. 路由守卫会在用户访问无权限页面时重定向到403页面
4. 用户信息和角色存储在 localStorage 中，刷新页面后会保持登录状态
5. 退出登录会清除所有用户信息和token

## 常见问题

### Q: 为什么我添加了权限指令但按钮还是显示？
A: 检查以下几点：
- 确认用户已登录且角色信息正确
- 确认权限标识符拼写正确
- 确认在 `ROLE_PERMISSIONS` 中正确配置了权限
- 检查浏览器控制台是否有错误

### Q: 如何让某个功能对所有角色开放？
A: 不添加 `v-permission` 指令，或者在所有角色的权限列表中都添加该权限

### Q: 如何实现更复杂的权限逻辑？
A: 在组件中使用 `computed` 属性结合权限判断函数：

```javascript
const canEdit = computed(() => {
  const role = userRole.value
  // 管理员可以编辑所有，其他人只能编辑自己的
  return role === ROLES.ADMIN || row.userId === currentUserId.value
})
```

## 更新日志

- 2024-12-25: 完成三个角色的权限差异化配置
- 2024-12-25: 修复预约管理、课程管理、仪表盘的权限控制
- 2024-12-25: 添加预约审批功能（仅管理员和教师可见）

