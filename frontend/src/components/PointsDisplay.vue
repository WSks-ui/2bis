<template>
  <div class="points-display" :class="[`points-display--${variant}`, { 'points-free': free }]">
    <span class="coin-icon">{{ iconText }}</span>
    <span class="points-value">{{ balance }}</span>
    <span class="points-label">{{ displayLabel }}</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  balance: {
    type: Number,
    default: 0
  },
  label: {
    type: String,
    default: ''
  },
  variant: {
    type: String,
    default: 'quota'
  },
  free: {
    type: Boolean,
    default: false
  }
})

const displayLabel = computed(() => {
  if (props.label) return props.label
  return props.free ? '体验积分' : '订阅额度'
})

const iconText = computed(() => {
  if (props.free || props.variant === 'experience') return 'E'
  return 'Q'
})
</script>

<style scoped>
.points-display {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-radius: 20px;
  background: rgba(120, 140, 93, 0.1);
  border: 1px solid rgba(120, 140, 93, 0.22);
  white-space: nowrap;
}

.points-display--experience,
.points-free {
  background: rgba(106, 155, 204, 0.1);
  border-color: rgba(106, 155, 204, 0.22);
}

.coin-icon {
  width: 18px;
  height: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-family: var(--font-heading);
  font-size: 10px;
  font-weight: 800;
  color: var(--color-dark);
  background: var(--color-green);
}

.points-display--experience .coin-icon,
.points-free .coin-icon {
  background: var(--color-blue);
}

.points-value {
  font-family: var(--font-heading);
  font-size: 14px;
  font-weight: 700;
  color: var(--color-light);
}

.points-label {
  font-family: var(--font-heading);
  font-size: 11px;
  font-weight: 600;
  color: var(--color-mid);
}

@media (max-width: 640px) {
  .points-label {
    display: none;
  }
}
</style>
