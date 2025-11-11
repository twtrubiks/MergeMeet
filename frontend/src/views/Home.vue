<template>
  <div class="home">
    <div class="container">
      <h1>🎉 歡迎使用 MergeMeet</h1>
      <p class="subtitle">交友平台開發環境已就緒</p>

      <div class="card">
        <h2>後端 API 狀態</h2>
        <div v-if="loading">載入中...</div>
        <div v-else-if="apiStatus">
          <p class="success">✅ {{ apiStatus.message }}</p>
          <p>版本: {{ apiStatus.version }}</p>
        </div>
        <div v-else class="error">
          ❌ 無法連接到後端 API
        </div>
      </div>

      <div class="info">
        <h3>開發資訊</h3>
        <ul>
          <li>前端: Vue 3 + Vite</li>
          <li>後端: FastAPI + Python</li>
          <li>資料庫: PostgreSQL + PostGIS</li>
          <li>快取: Redis</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const loading = ref(true)
const apiStatus = ref(null)

onMounted(async () => {
  try {
    const response = await axios.get('/api/hello')
    apiStatus.value = response.data
  } catch (error) {
    console.error('API 連接失敗:', error)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.home {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.container {
  max-width: 600px;
  width: 100%;
}

h1 {
  color: white;
  font-size: 3rem;
  margin-bottom: 1rem;
  text-align: center;
}

.subtitle {
  color: rgba(255, 255, 255, 0.9);
  font-size: 1.2rem;
  text-align: center;
  margin-bottom: 2rem;
}

.card {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
}

.card h2 {
  color: #333;
  margin-bottom: 1rem;
}

.success {
  color: #10b981;
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.error {
  color: #ef4444;
  font-weight: 600;
}

.info {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  padding: 1.5rem;
  color: white;
}

.info h3 {
  margin-bottom: 1rem;
}

.info ul {
  list-style: none;
}

.info li {
  padding: 0.5rem 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
}

.info li:last-child {
  border-bottom: none;
}
</style>
