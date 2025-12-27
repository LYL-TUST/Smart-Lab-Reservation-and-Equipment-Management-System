<template>
  <div class="error-page">
    <div class="error-content">
      <div class="error-icon">
        <el-icon :size="120" color="#f56c6c">
          <Lock />
        </el-icon>
      </div>
      <h1 class="error-code">403</h1>
      <h2 class="error-title">访问被拒绝</h2>
      <p class="error-description">
        抱歉，您没有权限访问此页面。<br>
        如需访问，请联系管理员获取相应权限。
      </p>
      <div class="error-actions">
        <el-button type="primary" @click="goBack">
          <el-icon><Back /></el-icon>
          返回上一页
        </el-button>
        <el-button @click="goHome">
          <el-icon><HomeFilled /></el-icon>
          返回首页
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { Lock, Back, HomeFilled } from '@element-plus/icons-vue'

const router = useRouter()

const goBack = () => {
  router.back()
}

const goHome = () => {
  router.push('/')
}
</script>

<style scoped>
.error-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.error-content {
  text-align: center;
  background: white;
  padding: 60px 40px;
  border-radius: 20px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  max-width: 600px;
  width: 100%;
}

.error-icon {
  margin-bottom: 30px;
  animation: shake 0.5s ease-in-out;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-10px); }
  75% { transform: translateX(10px); }
}

.error-code {
  font-size: 80px;
  font-weight: bold;
  color: #f56c6c;
  margin: 0 0 20px 0;
  line-height: 1;
}

.error-title {
  font-size: 32px;
  color: #303133;
  margin: 0 0 20px 0;
}

.error-description {
  font-size: 16px;
  color: #606266;
  line-height: 1.8;
  margin: 0 0 40px 0;
}

.error-actions {
  display: flex;
  gap: 15px;
  justify-content: center;
  flex-wrap: wrap;
}

@media (max-width: 768px) {
  .error-content {
    padding: 40px 20px;
  }
  
  .error-code {
    font-size: 60px;
  }
  
  .error-title {
    font-size: 24px;
  }
  
  .error-actions {
    flex-direction: column;
  }
  
  .error-actions .el-button {
    width: 100%;
  }
}
</style>

