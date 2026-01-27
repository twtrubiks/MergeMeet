<!--
  Icon.vue
  統一圖標包裝器 - 提供一致的大小和無障礙屬性

  使用方式:
  <Icon name="home" label="返回主選單" />
  <Icon name="heart" size="lg" />
  <Icon name="close" decorative />
-->
<template>
  <span
    class="icon-wrapper"
    :class="[sizeClass]"
    :aria-label="label"
    :aria-hidden="decorative || !label"
    :role="decorative ? 'presentation' : 'img'"
  >
    <n-icon :size="iconSize">
      <component :is="iconComponent" />
    </n-icon>
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { NIcon } from 'naive-ui'
import {
  HomeOutline,
  Heart,
  HeartOutline,
  HeartHalfOutline,
  HeartDislikeOutline,
  CloseOutline,
  Close,
  CloseCircleOutline,
  AlertCircleOutline,
  AlertCircle,
  LocationOutline,
  SearchOutline,
  ChatbubbleEllipses,
  ChatbubblesOutline,
  PersonOutline,
  PeopleOutline,
  SettingsOutline,
  LogOutOutline,
  ShieldOutline,
  ShieldCheckmarkOutline,
  ArrowBackOutline,
  RefreshOutline,
  TrashOutline,
  CheckmarkOutline,
  CheckmarkCircleOutline,
  CheckmarkDoneOutline,
  WarningOutline,
  InformationCircleOutline,
  Star,
  StarOutline,
  CameraOutline,
  TimeOutline,
  HourglassOutline,
  ClipboardOutline,
  LockClosedOutline,
  FlashOutline,
  RocketOutline,
  CreateOutline,
  EyeOutline,
  EyeOffOutline,
  MaleOutline,
  FemaleOutline,
  MaleFemaleOutline,
  SaveOutline,
  SyncOutline,
  HandLeftOutline,
  StatsChartOutline,
  ImageOutline,
  FlagOutline,
  BanOutline,
  DocumentTextOutline,
  ChevronForwardOutline,
  SendOutline,
  EllipsisVerticalOutline
} from '@vicons/ionicons5'

const props = defineProps({
  /**
   * 圖標名稱
   * @type {'home' | 'heart' | 'heart-outline' | 'heart-half' | 'heart-dislike' | 'close' | 'close-outline' | 'close-circle' | 'alert' | 'alert-outline' | 'location' | 'search' | 'chat' | 'chatbubbles' | 'person' | 'people' | 'settings' | 'logout' | 'shield' | 'shield-check' | 'back' | 'refresh' | 'trash' | 'check' | 'check-circle' | 'checkmark-done' | 'warning' | 'info' | 'star' | 'star-outline' | 'camera' | 'time' | 'hourglass' | 'clipboard' | 'lock' | 'flash' | 'rocket' | 'edit' | 'eye' | 'eye-off' | 'male' | 'female' | 'male-female' | 'save' | 'sync' | 'hand' | 'stats' | 'image' | 'flag' | 'ban' | 'document-text' | 'chevron-forward' | 'send' | 'ellipsis-vertical'}
   */
  name: {
    type: String,
    required: true
  },
  /**
   * 無障礙標籤 - 除非是裝飾性圖標，否則應提供
   */
  label: {
    type: String,
    default: ''
  },
  /**
   * 圖標大小
   * @type {'xs' | 'sm' | 'md' | 'lg' | 'xl'}
   */
  size: {
    type: String,
    default: 'md',
    validator: (value) => ['xs', 'sm', 'md', 'lg', 'xl'].includes(value)
  },
  /**
   * 是否為裝飾性圖標（純視覺，螢幕閱讀器會忽略）
   */
  decorative: {
    type: Boolean,
    default: false
  }
})

// 圖標映射
const iconMap = {
  'home': HomeOutline,
  'heart': Heart,
  'heart-outline': HeartOutline,
  'heart-half': HeartHalfOutline,
  'heart-dislike': HeartDislikeOutline,
  'close': Close,
  'close-outline': CloseOutline,
  'close-circle': CloseCircleOutline,
  'alert': AlertCircle,
  'alert-outline': AlertCircleOutline,
  'location': LocationOutline,
  'search': SearchOutline,
  'chat': ChatbubbleEllipses,
  'chatbubbles': ChatbubblesOutline,
  'person': PersonOutline,
  'people': PeopleOutline,
  'settings': SettingsOutline,
  'logout': LogOutOutline,
  'shield': ShieldOutline,
  'shield-check': ShieldCheckmarkOutline,
  'back': ArrowBackOutline,
  'refresh': RefreshOutline,
  'trash': TrashOutline,
  'check': CheckmarkOutline,
  'check-circle': CheckmarkCircleOutline,
  'checkmark-done': CheckmarkDoneOutline,
  'warning': WarningOutline,
  'info': InformationCircleOutline,
  'star': Star,
  'star-outline': StarOutline,
  'camera': CameraOutline,
  'time': TimeOutline,
  'hourglass': HourglassOutline,
  'clipboard': ClipboardOutline,
  'lock': LockClosedOutline,
  'flash': FlashOutline,
  'rocket': RocketOutline,
  'edit': CreateOutline,
  'eye': EyeOutline,
  'eye-off': EyeOffOutline,
  'male': MaleOutline,
  'female': FemaleOutline,
  'male-female': MaleFemaleOutline,
  'save': SaveOutline,
  'sync': SyncOutline,
  'hand': HandLeftOutline,
  'stats': StatsChartOutline,
  'image': ImageOutline,
  'flag': FlagOutline,
  'ban': BanOutline,
  'document-text': DocumentTextOutline,
  'chevron-forward': ChevronForwardOutline,
  'send': SendOutline,
  'ellipsis-vertical': EllipsisVerticalOutline
}

// 大小映射 (像素)
const sizeMap = {
  'xs': 14,
  'sm': 18,
  'md': 24,
  'lg': 32,
  'xl': 48
}

const iconComponent = computed(() => {
  return iconMap[props.name] || HomeOutline
})

const iconSize = computed(() => {
  return sizeMap[props.size]
})

const sizeClass = computed(() => {
  return `icon-${props.size}`
})
</script>

<style scoped>
.icon-wrapper {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  vertical-align: middle;
  line-height: 1;
}

/* 確保點擊區域符合 WCAG 觸控目標要求 */
.icon-lg,
.icon-xl {
  min-width: var(--touch-target-min);
  min-height: var(--touch-target-min);
}
</style>
