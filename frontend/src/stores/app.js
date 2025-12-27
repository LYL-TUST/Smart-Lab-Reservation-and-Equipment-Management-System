import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
    const isDark = ref(localStorage.getItem('theme') === 'dark')
    const sidebarCollapsed = ref(false)

    const toggleTheme = () => {
        isDark.value = !isDark.value
        localStorage.setItem('theme', isDark.value ? 'dark' : 'light')

        if (isDark.value) {
            document.documentElement.classList.add('dark')
        } else {
            document.documentElement.classList.remove('dark')
        }
    }

    const toggleSidebar = () => {
        sidebarCollapsed.value = !sidebarCollapsed.value
    }

    // 初始化主题
    if (isDark.value) {
        document.documentElement.classList.add('dark')
    }

    return {
        isDark,
        sidebarCollapsed,
        toggleTheme,
        toggleSidebar
    }
})

