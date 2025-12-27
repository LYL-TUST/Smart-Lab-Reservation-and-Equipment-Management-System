/**
 * 权限工具函数
 * 提供在组件中使用的权限检查方法
 */

import { computed } from 'vue'
import { useUserStore } from '../stores/user'
import { hasPermission, hasAnyPermission, hasAllPermissions, getUserPermissions } from '../config/permissions'

/**
 * 权限检查 Composable
 */
export function usePermission() {
  const userStore = useUserStore()
  
  const userRole = computed(() => userStore.userInfo?.role)
  const permissions = computed(() => getUserPermissions(userRole.value))
  
  /**
   * 检查是否有指定权限
   */
  const checkPermission = (permission) => {
    return hasPermission(userRole.value, permission)
  }
  
  /**
   * 检查是否有任一权限
   */
  const checkAnyPermission = (permissionList) => {
    return hasAnyPermission(userRole.value, permissionList)
  }
  
  /**
   * 检查是否有所有权限
   */
  const checkAllPermissions = (permissionList) => {
    return hasAllPermissions(userRole.value, permissionList)
  }
  
  /**
   * 检查是否是指定角色
   */
  const checkRole = (role) => {
    return userRole.value === role
  }
  
  /**
   * 检查是否是任一角色
   */
  const checkAnyRole = (roleList) => {
    return roleList.includes(userRole.value)
  }
  
  return {
    userRole,
    permissions,
    checkPermission,
    checkAnyPermission,
    checkAllPermissions,
    checkRole,
    checkAnyRole
  }
}

