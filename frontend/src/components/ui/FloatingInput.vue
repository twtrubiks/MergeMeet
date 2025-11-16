<template>
  <div class="floating-input" :class="{ 'has-value': hasValue, 'is-focused': isFocused, 'has-error': error }">
    <input
      :id="id"
      :type="type"
      :value="modelValue"
      :placeholder="placeholder"
      :required="required"
      :disabled="disabled"
      :autocomplete="autocomplete"
      @input="$emit('update:modelValue', $event.target.value)"
      @focus="isFocused = true"
      @blur="isFocused = false"
      class="input-field"
    />
    <label :for="id" class="input-label">
      {{ label }}
    </label>
    <div class="input-border"></div>
    <div v-if="error" class="error-message">{{ error }}</div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

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
  }
})

defineEmits(['update:modelValue'])

const isFocused = ref(false)
const hasValue = computed(() => props.modelValue !== '' && props.modelValue !== null)
</script>

<style scoped>
.floating-input {
  position: relative;
  margin-bottom: 24px;
}

.input-field {
  width: 100%;
  padding: 16px 16px 8px;
  border: 2px solid #e0e0e0;
  border-radius: 12px;
  font-size: 1rem;
  background: white;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  outline: none;
}

.input-field:focus {
  border-color: #667eea;
  box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1);
}

.input-field:disabled {
  background-color: #f5f5f5;
  cursor: not-allowed;
  opacity: 0.7;
}

.input-label {
  position: absolute;
  left: 16px;
  top: 50%;
  transform: translateY(-50%);
  color: #999;
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
  color: #667eea;
  font-weight: 600;
}

.floating-input.has-error .input-field {
  border-color: #f44336;
}

.floating-input.has-error .input-field:focus {
  box-shadow: 0 0 0 4px rgba(244, 67, 54, 0.1);
}

.floating-input.has-error .input-label {
  color: #f44336;
}

.input-border {
  position: absolute;
  bottom: 0;
  left: 50%;
  width: 0;
  height: 2px;
  background: linear-gradient(90deg, #667eea, #764ba2);
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
  color: #f44336;
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
  box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.15),
              0 8px 16px rgba(102, 126, 234, 0.1);
}
</style>
