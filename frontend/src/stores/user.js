import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUserStore = defineStore('user', () => {
    const token = ref(localStorage.getItem('token') || '')
    
    // 初始化 userInfo，确保有默认值
    const getInitialUserInfo = () => {
        try {
            const stored = localStorage.getItem('userInfo')
            return stored ? JSON.parse(stored) : {
                username: '',
                name: '',
                email: '',
                role: '',
                avatar: ''
            }
        } catch (error) {
            console.error('解析用户信息失败:', error)
            return {
                username: '',
                name: '',
                email: '',
                role: '',
                avatar: ''
            }
        }
    }
    
    const userInfo = ref(getInitialUserInfo())

    const setToken = (newToken) => {
        token.value = newToken
        localStorage.setItem('token', newToken)
    }

    const setUserInfo = (info) => {
        // 确保设置的用户信息包含所有必要字段
        userInfo.value = {
            username: info.username || '',
            name: info.name || '',
            email: info.email || '',
            role: info.role || '',
            avatar: info.avatar || '',
            ...info
        }
        localStorage.setItem('userInfo', JSON.stringify(userInfo.value))
    }

    const logout = () => {
        token.value = ''
        userInfo.value = {
            username: '',
            name: '',
            email: '',
            role: '',
            avatar: ''
        }
        localStorage.removeItem('token')
        localStorage.removeItem('userInfo')
    }

    return {
        token,
        userInfo,
        setToken,
        setUserInfo,
        logout
    }
})

