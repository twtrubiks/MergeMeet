<template>
  <Transition name="modal">
    <div v-if="show" class="modal-overlay" @click="handleClose">
      <div class="modal-container" @click.stop>
        <div class="modal-content">
          <!-- 配對成功圖示 -->
          <div class="match-icon">
            <div class="heart-animation">
              💕
            </div>
          </div>

          <!-- 標題 -->
          <h2 class="modal-title">配對成功！</h2>
          <p class="modal-subtitle">你們互相喜歡對方</p>

          <!-- 用戶資訊 -->
          <div v-if="matchedUser" class="user-info">
            <div class="user-avatar">
              <img
                v-if="matchedUser.profile_picture"
                :src="matchedUser.profile_picture"
                :alt="matchedUser.display_name"
              >
              <div v-else class="avatar-placeholder">
                {{ matchedUser.display_name[0] }}
              </div>
            </div>
            <h3 class="user-name">{{ matchedUser.display_name }}</h3>
            <p class="user-age">{{ matchedUser.age }} 歲</p>

            <!-- 共同興趣 -->
            <div v-if="matchedUser.interests && matchedUser.interests.length > 0" class="common-interests">
              <p class="interests-title">共同興趣</p>
              <div class="interests-tags">
                <span
                  v-for="interest in matchedUser.interests.slice(0, 3)"
                  :key="interest"
                  class="interest-tag"
                >
                  {{ interest }}
                </span>
              </div>
            </div>
          </div>

          <!-- 操作按鈕 -->
          <div class="modal-actions">
            <button class="btn-secondary" @click="handleClose">
              繼續探索
            </button>
            <button class="btn-primary" @click="goToMatches">
              查看配對
            </button>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { useRouter } from 'vue-router'

const props = defineProps({
  show: {
    type: Boolean,
    required: true
  },
  matchedUser: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close'])
const router = useRouter()

const handleClose = () => {
  emit('close')
}

const goToMatches = () => {
  emit('close')
  router.push('/matches')
}
</script>

<style scoped>
/* Modal 覆蓋層 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

/* Modal 容器 */
.modal-container {
  background: white;
  border-radius: 20px;
  max-width: 500px;
  width: 100%;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
  animation: slideUp 0.3s ease-out;
}

@keyframes slideUp {
  from {
    transform: translateY(50px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

/* Modal 內容 */
.modal-content {
  padding: 40px 30px 30px;
  text-align: center;
}

/* 配對成功圖示 */
.match-icon {
  margin-bottom: 20px;
}

.heart-animation {
  font-size: 80px;
  animation: heartBeat 1s ease-in-out infinite;
}

@keyframes heartBeat {
  0%, 100% {
    transform: scale(1);
  }
  25% {
    transform: scale(1.1);
  }
  50% {
    transform: scale(1);
  }
  75% {
    transform: scale(1.15);
  }
}

/* 標題 */
.modal-title {
  font-size: 28px;
  font-weight: 700;
  color: #FF6B6B;
  margin: 0 0 10px;
}

.modal-subtitle {
  font-size: 16px;
  color: #666;
  margin: 0 0 30px;
}

/* 用戶資訊 */
.user-info {
  margin-bottom: 30px;
}

.user-avatar {
  width: 120px;
  height: 120px;
  margin: 0 auto 15px;
  border-radius: 50%;
  overflow: hidden;
  border: 4px solid #FF6B6B;
  box-shadow: 0 4px 12px rgba(255, 107, 107, 0.3);
}

.user-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #FF6B6B, #FF8E53);
  color: white;
  font-size: 48px;
  font-weight: bold;
}

.user-name {
  font-size: 24px;
  font-weight: 600;
  color: #333;
  margin: 0 0 5px;
}

.user-age {
  font-size: 16px;
  color: #666;
  margin: 0 0 20px;
}

/* 共同興趣 */
.common-interests {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #eee;
}

.interests-title {
  font-size: 14px;
  color: #999;
  margin: 0 0 10px;
}

.interests-tags {
  display: flex;
  gap: 8px;
  justify-content: center;
  flex-wrap: wrap;
}

.interest-tag {
  display: inline-block;
  padding: 6px 14px;
  background: #FFF0F0;
  color: #FF6B6B;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 500;
}

/* 操作按鈕 */
.modal-actions {
  display: flex;
  gap: 12px;
}

.modal-actions button {
  flex: 1;
  padding: 14px 20px;
  border: none;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-primary {
  background: linear-gradient(135deg, #FF6B6B, #FF8E53);
  color: white;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(255, 107, 107, 0.4);
}

.btn-secondary {
  background: #f5f5f5;
  color: #666;
}

.btn-secondary:hover {
  background: #e0e0e0;
}

/* Modal 過渡效果 */
.modal-enter-active, .modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-from, .modal-leave-to {
  opacity: 0;
}

/* 響應式設計 */
@media (max-width: 768px) {
  .modal-content {
    padding: 30px 20px 20px;
  }

  .modal-title {
    font-size: 24px;
  }

  .user-avatar {
    width: 100px;
    height: 100px;
  }

  .user-name {
    font-size: 20px;
  }

  .modal-actions {
    flex-direction: column;
  }
}
</style>
