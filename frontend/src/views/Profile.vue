<template>
  <div class="profile">
    <el-row :gutter="20">
      <!-- 左侧个人信息卡片 -->
      <el-col :xs="24" :md="8">
        <el-card class="profile-card">
          <div class="avatar-section">
            <el-avatar :size="120" :src="userInfo.avatar">
              <el-icon :size="60"><UserFilled /></el-icon>
            </el-avatar>
            <el-button type="primary" text class="upload-btn" @click="handleUploadAvatar">
              <el-icon><Upload /></el-icon>
              更换头像
            </el-button>
          </div>
          <div class="user-info">
            <h2>{{ userInfo.username }}</h2>
            <el-tag :type="getRoleType(userInfo.role)" class="role-tag">
              {{ getRoleText(userInfo.role) }}
            </el-tag>
            <div class="info-item">
              <el-icon><Message /></el-icon>
              <span>{{ userInfo.email }}</span>
            </div>
            <div class="info-item">
              <el-icon><Phone /></el-icon>
              <span>{{ userInfo.phone || '未设置' }}</span>
            </div>
            <div class="info-item">
              <el-icon><Calendar /></el-icon>
              <span>加入时间: {{ userInfo.createdAt }}</span>
            </div>
          </div>
        </el-card>

        <!-- 统计卡片 -->
        <el-card class="stats-card">
          <template #header>
            <span>我的统计</span>
          </template>
          <div class="stat-item">
            <div class="stat-label">总预约数</div>
            <div class="stat-value">{{ stats.totalReservations }}</div>
          </div>
          <el-divider />
          <div class="stat-item">
            <div class="stat-label">待审核</div>
            <div class="stat-value text-warning">{{ stats.pendingReservations }}</div>
          </div>
          <el-divider />
          <div class="stat-item">
            <div class="stat-label">已完成</div>
            <div class="stat-value text-success">{{ stats.completedReservations }}</div>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧信息编辑 -->
      <el-col :xs="24" :md="16">
        <el-card>
          <template #header>
            <span>个人信息</span>
          </template>
          <el-form
            ref="formRef"
            :model="form"
            :rules="rules"
            label-width="100px"
          >
            <el-form-item label="用户名" prop="username">
              <el-input v-model="form.username" disabled />
            </el-form-item>
            <el-form-item label="邮箱" prop="email">
              <el-input v-model="form.email" />
            </el-form-item>
            <el-form-item label="电话" prop="phone">
              <el-input v-model="form.phone" />
            </el-form-item>
            <el-form-item label="真实姓名" prop="realName">
              <el-input v-model="form.realName" />
            </el-form-item>
            <el-form-item label="学号/工号" prop="idNumber">
              <el-input v-model="form.idNumber" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleUpdateInfo" :loading="updating">
                保存修改
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card style="margin-top: 20px;">
          <template #header>
            <span>修改密码</span>
          </template>
          <el-form
            ref="passwordFormRef"
            :model="passwordForm"
            :rules="passwordRules"
            label-width="100px"
          >
            <el-form-item label="原密码" prop="oldPassword">
              <el-input v-model="passwordForm.oldPassword" type="password" show-password />
            </el-form-item>
            <el-form-item label="新密码" prop="newPassword">
              <el-input v-model="passwordForm.newPassword" type="password" show-password />
            </el-form-item>
            <el-form-item label="确认密码" prop="confirmPassword">
              <el-input v-model="passwordForm.confirmPassword" type="password" show-password />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleChangePassword" :loading="changingPassword">
                修改密码
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { UserFilled, Upload, Message, Phone, Calendar } from '@element-plus/icons-vue'
import { useUserStore } from '../stores/user'

const userStore = useUserStore()
const formRef = ref(null)
const passwordFormRef = ref(null)
const updating = ref(false)
const changingPassword = ref(false)

const userInfo = reactive({
  username: userStore.userInfo.username || '',
  email: userStore.userInfo.email || '',
  phone: userStore.userInfo.phone || '',
  role: userStore.userInfo.role || 'STUDENT',
  avatar: userStore.userInfo.avatar || '',
  createdAt: userStore.userInfo.createdAt || '',
  realName: userStore.userInfo.name || '',
  idNumber: userStore.userInfo.studentId || ''
})

const stats = reactive({
  totalReservations: 25,
  pendingReservations: 3,
  completedReservations: 20
})

const form = reactive({
  username: userInfo.username,
  email: userInfo.email,
  phone: userInfo.phone,
  realName: userInfo.realName,
  idNumber: userInfo.idNumber
})

const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const rules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  phone: [
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' }
  ]
}

const passwordRules = {
  oldPassword: [
    { required: true, message: '请输入原密码', trigger: 'blur' }
  ],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能小于6位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== passwordForm.newPassword) {
          callback(new Error('两次输入密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

const getRoleType = (role) => {
  const typeMap = {
    'ADMIN': 'danger',
    'TEACHER': 'warning',
    'STUDENT': 'success'
  }
  return typeMap[role] || 'info'
}

const getRoleText = (role) => {
  const textMap = {
    'ADMIN': '管理员',
    'TEACHER': '教师',
    'STUDENT': '学生'
  }
  return textMap[role] || role
}

const handleUploadAvatar = () => {
  ElMessage.info('上传头像功能开发中...')
}

const handleUpdateInfo = async () => {
  await formRef.value.validate(async (valid) => {
    if (valid) {
      updating.value = true
      try {
        await new Promise(resolve => setTimeout(resolve, 1000))
        Object.assign(userInfo, form)
        ElMessage.success('信息更新成功')
      } catch (error) {
        console.error(error)
      } finally {
        updating.value = false
      }
    }
  })
}

const handleChangePassword = async () => {
  await passwordFormRef.value.validate(async (valid) => {
    if (valid) {
      changingPassword.value = true
      try {
        await new Promise(resolve => setTimeout(resolve, 1000))
        ElMessage.success('密码修改成功')
        passwordFormRef.value.resetFields()
      } catch (error) {
        console.error(error)
      } finally {
        changingPassword.value = false
      }
    }
  })
}
</script>

<style scoped>
.profile {
  width: 100%;
}

.profile-card {
  margin-bottom: 20px;
}

.avatar-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px 0;
  border-bottom: 1px solid var(--border-color);
}

.upload-btn {
  margin-top: 15px;
}

.user-info {
  padding: 20px 0;
  text-align: center;
}

.user-info h2 {
  margin: 10px 0;
  font-size: 24px;
  color: var(--text-primary);
}

.role-tag {
  margin-bottom: 20px;
}

.info-item {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin: 10px 0;
  color: var(--text-regular);
  font-size: 14px;
}

.stats-card {
  margin-bottom: 20px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
}

.stat-label {
  font-size: 14px;
  color: var(--text-secondary);
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: var(--text-primary);
}

.text-warning {
  color: var(--warning-color);
}

.text-success {
  color: var(--success-color);
}

@media (max-width: 768px) {
  .user-info h2 {
    font-size: 20px;
  }
  
  .stat-value {
    font-size: 20px;
  }
}
</style>

