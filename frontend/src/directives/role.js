/**
 * 角色指令
 * 用于控制页面元素的显示/隐藏（基于角色）
 * 
 * 使用方法：
 * v-role="'ADMIN'"  // 单个角色
 * v-role="['ADMIN', 'TEACHER']"  // 多个角色（任一）
 */

import { useUserStore } from '../stores/user'

export default {
  mounted(el, binding) {
    const userStore = useUserStore()
    const userRole = userStore.userInfo?.role
    
    if (!userRole) {
      // 如果没有角色信息，隐藏元素
      el.style.display = 'none'
      return
    }
    
    const { value } = binding
    let hasRole = false
    
    if (Array.isArray(value)) {
      // 多个角色，拥有任一即可
      hasRole = value.includes(userRole)
    } else if (typeof value === 'string') {
      // 单个角色
      hasRole = userRole === value
    }
    
    if (!hasRole) {
      // 没有对应角色，移除元素
      el.parentNode && el.parentNode.removeChild(el)
    }
  }
}

