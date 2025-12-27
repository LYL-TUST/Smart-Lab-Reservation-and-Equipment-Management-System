<template>
  <router-view v-slot="{ Component }">
    <transition name="fade" mode="out-in">
      <component :is="Component" />
    </transition>
  </router-view>
</template>

<script setup>
import { onMounted } from 'vue'
import { useAppStore } from './stores/app'

const appStore = useAppStore()

onMounted(() => {
  // 初始化主题
  if (appStore.isDark) {
    document.documentElement.classList.add('dark')
  }
})
</script>

<style>
/* 全局样式已在 style.css 中定义 */
</style>
