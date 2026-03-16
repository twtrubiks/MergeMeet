<template>
  <div
    class="floating-input"
    :class="{
      'has-value': hasValue,
      'is-focused': isFocused,
      'has-error': error,
      'has-toggle': showPasswordToggle && type === 'password'
    }"
  >
    <input
      :id="id"
      :type="computedType"
      :value="modelValue"
      :placeholder="placeholder"
      :required="required"
      :disabled="disabled"
      :autocomplete="autocomplete"
      :aria-invalid="!!error"
      :aria-describedby="error ? `${id}-error` : undefined"
      class="input-field"
      @input="$emit('update:modelValue', $event.target.value)"
      @focus="isFocused = true"
      @blur="isFocused = false"
    />
    <label :for="id" class="input-label">
      {{ label }}
    </label>
    <button
      v-if="showPasswordToggle && type === 'password'"
      type="button"
      class="password-toggle"
      :aria-label="showPassword ? '隱藏密碼' : '顯示密碼'"
      @click="togglePasswordVisibility"
    >
      <Icon :name="showPassword ? 'eye-off' : 'eye'" size="sm" decorative />
    </button>
    <div class="input-border"></div>
    <div v-if="error" :id="`${id}-error`" class="error-message" role="alert" aria-live="assertive">
      {{ error }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import Icon from '@/components/ui/Icon.vue'

const props = defineProps({
  id: {
    type: String,
    required: true
  },
  label: {
    type: String,
    required: true
  },
  type: {
    type: String,
    default: 'text'
  },
  modelValue: {
    type: [String, Number],
    default: ''
  },
  placeholder: {
    type: String,
    default: ''
  },
  required: {
    type: Boolean,
    default: false
  },
  disabled: {
    type: Boolean,
    default: false
  },
  autocomplete: {
    type: String,
    default: 'off'
  },
  error: {
    type: String,
    default: ''
  },
  showPasswordToggle: {
    type: Boolean,
    default: false
  }
})

defineEmits(['update:modelValue'])

const isFocused = ref(false)
const showPassword = ref(false)

const hasValue = computed(() => props.modelValue !== '' && props.modelValue !== null)

// 計算實際的 input type（用於密碼顯示切換）
const computedType = computed(() => {
  if (props.type === 'password' && props.showPasswordToggle && showPassword.value) {
    return 'text'
  }
  return props.type
})

// 切換密碼顯示
const togglePasswordVisibility = () => {
  showPassword.value = !showPassword.value
}
</script>

<style scoped>
.floating-input {
  position: relative;
  margin-bottom: var(--space-6);
}

.input-field {
  width: 100%;
  padding: 16px 16px 8px;
  border: 2px solid var(--color-border);
  border-radius: 12px;
  font-size: 1rem;
  background: white;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  outline: none;
}

.input-field:focus {
  border-color: var(--color-primary-500);
  box-shadow: 0 0 0 4px var(--color-primary-alpha-10);
}

.input-field:disabled {
  background-color: var(--color-background-light);
  cursor: not-allowed;
  opacity: 0.7;
}

.input-label {
  position: absolute;
  left: 16px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--color-text-light);
  font-size: 1rem;
  pointer-events: none;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  background: white;
  padding: 0 4px;
}

.floating-input.has-value .input-label,
.floating-input.is-focused .input-label {
  top: 0;
  font-size: 0.75rem;
  color: var(--color-primary-500);
  font-weight: 600;
}

.floating-input.has-error .input-field {
  border-color: var(--color-error-500);
}

.floating-input.has-error .input-field:focus {
  box-shadow: 0 0 0 4px var(--color-error-alpha-10);
}

.floating-input.has-error .input-label {
  color: var(--color-error-500);
}

.input-border {
  position: absolute;
  bottom: 0;
  left: 50%;
  width: 0;
  height: 2px;
  background: var(--color-primary-gradient);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  transform: translateX(-50%);
}

.floating-input.is-focused .input-border {
  width: 100%;
}

.error-message {
  position: absolute;
  top: 100%;
  left: 0;
  font-size: 0.75rem;
  color: var(--color-error-500);
  margin-top: 4px;
  animation: slideDown 0.3s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Glow effect on focus */
.floating-input.is-focused .input-field {
  box-shadow:
    0 0 0 4px var(--color-primary-alpha-20),
    0 8px 16px var(--color-primary-alpha-10);
}

/* Password toggle button */
.floating-input.has-toggle .input-field {
  padding-right: 48px;
}

.password-toggle {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  padding: 8px;
  cursor: pointer;
  color: var(--color-text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: all 0.2s ease;
}

.password-toggle:hover {
  background: var(--color-primary-alpha-10);
  color: var(--color-primary-500);
}

.password-toggle:focus {
  outline: 2px solid var(--color-primary-500);
  outline-offset: 2px;
}

.floating-input.has-error .password-toggle {
  top: calc(50% - 10px);
}

@media (max-width: 480px) {
  .floating-input {
    margin-bottom: var(--space-5);
  }

  .input-field {
    padding: var(--space-3) var(--space-3) var(--space-2);
    font-size: var(--font-size-base);
  }
}
</style>
