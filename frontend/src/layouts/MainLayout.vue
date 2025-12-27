<template>
  <div class="main-layout">
    <!-- 侧边栏 -->
    <el-aside :width="sidebarWidth" class="sidebar">
      <div class="logo-section">
        <el-icon :size="32" color="#409eff">
          <Monitor />
        </el-icon>
        <transition name="fade">
          <span v-show="!appStore.sidebarCollapsed" class="logo-text">智能实验室</span>
        </transition>
      </div>

      <el-menu
        :default-active="activeMenu"
        :collapse="appStore.sidebarCollapsed"
        :collapse-transition="false"
        router
        class="sidebar-menu"
      >
        <el-menu-item
          v-for="route in menuRoutes"
          :key="route.path"
          :index="route.path"
        >
          <el-icon>
            <component :is="route.meta.icon" />
          </el-icon>
          <template #title>{{ route.meta.title }}</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 主内容区 -->
    <el-container class="main-container">
      <!-- 顶部导航栏 -->
      <el-header class="header">
        <div class="header-left">
          <el-button
            :icon="appStore.sidebarCollapsed ? Expand : Fold"
            circle
            @click="appStore.toggleSidebar"
          />
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="currentRoute">{{ currentRoute.meta.title }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>

        <div class="header-right">
          <!-- 主题切换 -->
          <el-tooltip :content="appStore.isDark ? '切换到亮色模式' : '切换到暗黑模式'">
            <el-button
              :icon="appStore.isDark ? Sunny : Moon"
              circle
              @click="appStore.toggleTheme"
            />
          </el-tooltip>

          <!-- 通知 -->
          <el-badge :value="3" class="notification-badge">
            <el-button :icon="Bell" circle />
          </el-badge>

          <!-- 用户菜单 -->
          <el-dropdown @command="handleCommand">
            <div class="user-info">
              <el-avatar :size="35" :src="userStore.userInfo?.avatar">
                <el-icon><UserFilled /></el-icon>
              </el-avatar>
              <span class="username">{{ userStore.userInfo?.username || '用户' }}</span>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">
                  <el-icon><User /></el-icon>
                  个人中心
                </el-dropdown-item>
                <el-dropdown-item command="settings">
                  <el-icon><Setting /></el-icon>
                  设置
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 内容区域 -->
      <el-main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="slide-fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import {
  Monitor,
  Expand,
  Fold,
  Sunny,
  Moon,
  Bell,
  UserFilled,
  User,
  Setting,
  SwitchButton
} from '@element-plus/icons-vue'
import { useAppStore } from '../stores/app'
import { useUserStore } from '../stores/user'
import { hasAnyPermission } from '../config/permissions'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const userStore = useUserStore()

const sidebarWidth = computed(() => {
  return appStore.sidebarCollapsed ? '64px' : '240px'
})

const activeMenu = computed(() => {
  return route.path
})

const currentRoute = computed(() => {
  return route
})

const menuRoutes = computed(() => {
  const allRoutes = router.options.routes
    .find(r => r.path === '/')
    ?.children.filter(r => r.meta?.title && !r.meta?.hidden) || []
  
  // 根据用户角色过滤菜单
  const userRole = userStore.userInfo?.role
  if (!userRole) return []
  
  return allRoutes.filter(route => {
    // 如果路由指定了角色限制
    if (route.meta?.roles && route.meta.roles.length > 0) {
      return route.meta.roles.includes(userRole)
    }
    
    // 如果路由指定了权限要求
    if (route.meta?.permissions && route.meta.permissions.length > 0) {
      return hasAnyPermission(userRole, route.meta.permissions)
    }
    
    // 默认显示
    return true
  })
})

const handleCommand = (command) => {
  switch (command) {
    case 'profile':
      router.push('/profile')
      break
    case 'settings':
      ElMessage.info('设置功能开发中...')
      break
    case 'logout':
      ElMessageBox.confirm('确定要退出登录吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        userStore.logout()
        router.push('/login')
        ElMessage.success('已退出登录')
      }).catch(() => {})
      break
  }
}
</script>

<style scoped>
.main-layout {
  display: flex;
  width: 100%;
  height: 100vh;
  overflow: hidden;
}

.sidebar {
  background: var(--card-bg);
  border-right: 1px solid var(--border-color);
  transition: width 0.3s ease;
  overflow-x: hidden;
}

.logo-section {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 60px;
  padding: 0 20px;
  border-bottom: 1px solid var(--border-color);
  gap: 10px;
}

.logo-text {
  font-size: 18px;
  font-weight: bold;
  color: var(--text-primary);
  white-space: nowrap;
}

.sidebar-menu {
  border: none;
  background: transparent;
}

.main-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  background: var(--card-bg);
  border-bottom: 1px solid var(--border-color);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 20px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 15px;
}

.notification-badge {
  cursor: pointer;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 5px 10px;
  cursor: pointer;
  border-radius: 20px;
  transition: background 0.3s ease;
}

.user-info:hover {
  background: var(--bg-color);
}

.username {
  font-size: 14px;
  color: var(--text-primary);
}

.main-content {
  flex: 1;
  padding: 20px;
  background: var(--bg-color);
  overflow-y: auto;
}

@media (max-width: 768px) {
  .username {
    display: none;
  }
  
  .header-left {
    gap: 10px;
  }
  
  .header-right {
    gap: 10px;
  }
}
</style>

