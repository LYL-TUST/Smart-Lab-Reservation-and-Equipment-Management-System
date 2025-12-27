# 权限系统使用指南

## 📋 权限系统概述

本系统实现了基于角色的访问控制（RBAC），支持三种角色：
- **ADMIN（管理员）**：拥有所有权限
- **TEACHER（教师）**：可以管理实验室、设备、课程，审批预约
- **STUDENT（学生）**：只能查看和预约，管理自己的预约

## 🎯 角色权限对比

### 管理员 (ADMIN)
- ✅ 所有功能的完整访问权限
- ✅ 用户管理
- ✅ 系统配置

### 教师 (TEACHER)
- ✅ 查看和创建预约
- ✅ **审批预约**（学生预约需要教师审批）
- ✅ 编辑实验室信息
- ✅ 管理和维护设备
- ✅ 创建和管理课程
- ❌ 无法访问用户管理
- ❌ 无法删除实验室

### 学生 (STUDENT)
- ✅ 查看实验室、设备、课程
- ✅ 创建预约申请
- ✅ 管理自己的预约（编辑/删除）
- ❌ 无法审批预约
- ❌ 无法管理实验室
- ❌ 无法管理设备
- ❌ 无法管理课程
- ❌ 无法访问用户管理

## 🔧 使用方法

### 1. 在模板中使用指令

#### v-permission 指令（基于权限）
```vue
<template>
  <!-- 单个权限 -->
  <el-button v-permission="'reservation:approve'">
    审批预约
  </el-button>
  
  <!-- 多个权限（任一） -->
  <el-button v-permission="['lab:edit', 'lab:delete']">
    管理实验室
  </el-button>
  
  <!-- 多个权限（全部） -->
  <el-button v-permission.all="['equipment:edit', 'equipment:maintain']">
    设备维护
  </el-button>
</template>
```

#### v-role 指令（基于角色）
```vue
<template>
  <!-- 单个角色 -->
  <div v-role="'ADMIN'">
    管理员专属内容
  </div>
  
  <!-- 多个角色 -->
  <div v-role="['ADMIN', 'TEACHER']">
    管理员和教师可见
  </div>
</template>
```

### 2. 在脚本中使用 Composable

```vue
<script setup>
import { usePermission } from '@/composables/usePermission'
import { PERMISSIONS, ROLES } from '@/config/permissions'

const { 
  userRole, 
  checkPermission, 
  checkRole,
  checkAnyPermission 
} = usePermission()

// 检查权限
const canApprove = checkPermission(PERMISSIONS.RESERVATION_APPROVE)
const canManageLab = checkAnyPermission([
  PERMISSIONS.LAB_EDIT, 
  PERMISSIONS.LAB_DELETE
])

// 检查角色
const isAdmin = checkRole(ROLES.ADMIN)
const isTeacherOrAdmin = checkAnyRole([ROLES.ADMIN, ROLES.TEACHER])

// 根据权限执行操作
const handleApprove = () => {
  if (!canApprove) {
    ElMessage.error('您没有审批权限')
    return
  }
  // 执行审批逻辑
}
</script>
```

### 3. 路由权限配置

在 `router/index.js` 中配置路由权限：

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

## 📝 实际应用示例

### 示例1：预约管理页面

```vue
<template>
  <div class="reservations">
    <!-- 所有角色都能看到预约列表 -->
    <el-table :data="reservations">
      <el-table-column prop="labName" label="实验室" />
      <el-table-column prop="date" label="日期" />
      <el-table-column label="操作">
        <template #default="{ row }">
          <!-- 学生只能编辑自己的预约 -->
          <el-button 
            v-if="row.userId === currentUserId"
            v-permission="'reservation:edit'"
            @click="handleEdit(row)"
          >
            编辑
          </el-button>
          
          <!-- 只有教师和管理员能审批 -->
          <el-button 
            v-permission="'reservation:approve'"
            type="success"
            @click="handleApprove(row)"
          >
            审批
          </el-button>
          
          <!-- 管理员可以管理所有预约 -->
          <el-button 
            v-permission="'reservation:manage'"
            type="danger"
            @click="handleDelete(row)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <!-- 创建预约按钮（所有角色都可以） -->
    <el-button 
      v-permission="'reservation:create'"
      type="primary"
      @click="handleCreate"
    >
      创建预约
    </el-button>
  </div>
</template>
```

### 示例2：实验室管理页面

```vue
<template>
  <div class="laboratories">
    <!-- 所有角色都能查看 -->
    <el-table :data="laboratories">
      <el-table-column prop="name" label="实验室名称" />
      <el-table-column label="操作">
        <template #default="{ row }">
          <!-- 教师和管理员可以编辑 -->
          <el-button 
            v-permission="'lab:edit'"
            @click="handleEdit(row)"
          >
            编辑
          </el-button>
          
          <!-- 只有管理员可以删除 -->
          <el-button 
            v-permission="'lab:delete'"
            type="danger"
            @click="handleDelete(row)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <!-- 只有管理员可以创建实验室 -->
    <el-button 
      v-permission="'lab:create'"
      type="primary"
      @click="handleCreate"
    >
      创建实验室
    </el-button>
  </div>
</template>
```

### 示例3：设备管理页面

```vue
<template>
  <div class="equipment">
    <el-table :data="equipmentList">
      <el-table-column prop="name" label="设备名称" />
      <el-table-column prop="status" label="状态" />
      <el-table-column label="操作">
        <template #default="{ row }">
          <!-- 教师和管理员可以维护设备 -->
          <el-button 
            v-permission="'equipment:maintain'"
            @click="handleMaintain(row)"
          >
            维护记录
          </el-button>
          
          <!-- 只有管理员可以删除设备 -->
          <el-button 
            v-permission="'equipment:delete'"
            type="danger"
            @click="handleDelete(row)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>
```

## 🔐 权限列表

### 仪表盘
- `dashboard:view` - 查看仪表盘

### 预约管理
- `reservation:view` - 查看预约
- `reservation:create` - 创建预约
- `reservation:edit` - 编辑自己的预约
- `reservation:delete` - 删除自己的预约
- `reservation:approve` - 审批预约（教师、管理员）
- `reservation:manage` - 管理所有预约（管理员）

### 实验室管理
- `lab:view` - 查看实验室
- `lab:create` - 创建实验室（管理员）
- `lab:edit` - 编辑实验室（教师、管理员）
- `lab:delete` - 删除实验室（管理员）
- `lab:manage` - 管理实验室（管理员）

### 设备管理
- `equipment:view` - 查看设备
- `equipment:create` - 创建设备（管理员）
- `equipment:edit` - 编辑设备（教师、管理员）
- `equipment:delete` - 删除设备（管理员）
- `equipment:maintain` - 设备维护（教师、管理员）

### 课程管理
- `course:view` - 查看课程
- `course:create` - 创建课程（教师、管理员）
- `course:edit` - 编辑课程（教师、管理员）
- `course:delete` - 删除课程（教师、管理员）

### 用户管理
- `user:view` - 查看用户（管理员）
- `user:create` - 创建用户（管理员）
- `user:edit` - 编辑用户（管理员）
- `user:delete` - 删除用户（管理员）
- `user:manage` - 管理用户（管理员）

## 🚀 测试账号

- **管理员**: admin / 123456
- **教师**: teacher / 123456
- **学生**: student / 123456

## 📌 注意事项

1. **前后端权限一致性**：确保前端权限控制与后端API权限验证保持一致
2. **权限粒度**：根据实际业务需求调整权限粒度
3. **用户体验**：对于没有权限的功能，可以选择隐藏或禁用，并给出友好提示
4. **安全性**：前端权限控制主要用于UI展示，真正的安全验证必须在后端进行

