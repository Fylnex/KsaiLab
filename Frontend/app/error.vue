<script setup lang="ts">
import type { NuxtError } from '#app'

const props = defineProps<{
  error: NuxtError
}>()

useSeoMeta({
  title: 'Page not found',
  description: 'We are sorry but this page could not be found.'
})

useHead({
  htmlAttrs: {
    lang: 'en'
  }
})

const handleError = () => clearError({ redirect: '/' })
</script>

<template>
  <div class="error-page">
    <img 
      src="/404.png" 
      alt="404 Page Not Found" 
      class="error-image"
    />
    <div class="error-overlay">
      <button 
        @click="handleError" 
        class="back-button"
      >
        Вернуться на главную
      </button>
    </div>
  </div>
</template>

<style scoped>
.error-page {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  margin: 0;
  padding: 0;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.error-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
}

.error-overlay {
  position: absolute;
  bottom: 40px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;
}

.back-button {
  padding: 12px 24px;
  background-color: rgba(255, 255, 255, 0.9);
  border: 2px solid #1b1718;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #1b1718;
  cursor: pointer;
  transition: all 0.3s ease;
}

.back-button:hover {
  background-color: #1b1718;
  color: white;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}
</style>
