/**
 * 权限指令
 * 用于控制页面元素的显示/隐藏
 * 
 * 使用方法：
 * v-permission="'permission:key'"  // 单个权限
 * v-permission="['permission:key1', 'permission:key2']"  // 多个权限（任一）
 * v-permission.all="['permission:key1', 'permission:key2']"  // 多个权限（全部）
 */

import { useUserStore } from '../stores/user'
import { hasPermission, hasAnyPermission, hasAllPermissions } from '../config/permissions'

export default {
  mounted(el, binding) {
    const userStore = useUserStore()
    const userRole = userStore.userInfo?.role
    
    if (!userRole) {
      // 如果没有角色信息，隐藏元素
      el.style.display = 'none'
      return
    }
    
    const { value, modifiers } = binding
    let hasAuth = false
    
    if (Array.isArray(value)) {
      // 多个权限
      if (modifiers.all) {
        // 需要拥有所有权限
        hasAuth = hasAllPermissions(userRole, value)
      } else {
        // 拥有任一权限即可
        hasAuth = hasAnyPermission(userRole, value)
      }
    } else if (typeof value === 'string') {
      // 单个权限
      hasAuth = hasPermission(userRole, value)
    }
    
    if (!hasAuth) {
      // 没有权限，移除元素
      el.parentNode && el.parentNode.removeChild(el)
    }
  }
}

