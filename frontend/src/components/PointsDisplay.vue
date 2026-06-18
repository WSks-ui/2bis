<template>
  <div
    class="points-display"
    :class="[`points-display--${variant}`, { 'points-free': free, 'points-display--empty': isEmpty }]"
    :aria-label="ariaLabel"
    data-spotlight
  >
    <span class="coin-icon" aria-hidden="true">
      <span class="coin-core">{{ iconText }}</span>
    </span>
    <span class="points-copy">
      <span class="points-label">{{ displayLabel }}</span>
      <span class="points-value">{{ formattedBalance }}</span>
    </span>
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

const normalizedBalance = computed(() => {
  const value = Number(props.balance)
  return Number.isFinite(value) ? value : 0
})

const formattedBalance = computed(() => new Intl.NumberFormat('zh-CN').format(normalizedBalance.value))

const isEmpty = computed(() => normalizedBalance.value <= 0)

const ariaLabel = computed(() => `${displayLabel.value} ${formattedBalance.value}`)

const iconText = computed(() => {
  if (props.free || props.variant === 'experience') return 'E'
  return 'Q'
})
</script>

<style scoped>
.points-display {
  --points-accent: 63, 140, 104;
  --points-ink: var(--color-green);
  position: relative;
  min-height: 38px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 5px 11px 5px 6px;
  border: 1px solid rgba(var(--points-accent), 0.2);
  border-radius: 999px;
  background:
    linear-gradient(135deg, rgba(var(--points-accent), 0.1), rgba(255, 255, 255, 0.72) 56%),
    rgba(255, 255, 255, 0.66);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8), 0 8px 22px rgba(23, 23, 23, 0.045);
  white-space: nowrap;
  isolation: isolate;
  transform: translateZ(0);
  transition:
    border-color var(--transition-base),
    box-shadow var(--transition-base),
    transform var(--transition-base),
    background var(--transition-base);
}

.points-display:hover {
  border-color: rgba(var(--points-accent), 0.34);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.88), 0 12px 28px rgba(var(--points-accent), 0.12);
  transform: translate3d(0, -1px, 0);
}

.points-display--experience,
.points-free {
  --points-accent: 60, 110, 232;
  --points-ink: var(--color-blue);
}

.coin-icon {
  position: relative;
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background:
    radial-gradient(circle at 34% 28%, rgba(255, 255, 255, 0.92), transparent 34%),
    linear-gradient(135deg, rgba(var(--points-accent), 0.96), rgba(var(--points-accent), 0.56));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.62), 0 8px 16px rgba(var(--points-accent), 0.2);
}

.coin-icon::after {
  content: '';
  position: absolute;
  inset: 4px;
  border: 1px solid rgba(255, 255, 255, 0.46);
  border-radius: inherit;
}

.coin-core {
  font-family: var(--font-heading);
  font-size: 10px;
  font-weight: 900;
  color: #fff;
  letter-spacing: -0.04em;
}

.points-copy {
  display: grid;
  gap: 1px;
  line-height: 1;
}

.points-value {
  font-family: var(--font-heading);
  font-size: 15px;
  font-weight: 850;
  color: var(--points-ink);
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
  transition: color var(--transition-base), transform var(--transition-base);
}

.points-display:hover .points-value {
  transform: translateX(1px);
}

.points-label {
  font-family: var(--font-heading);
  font-size: 10px;
  font-weight: 800;
  color: var(--color-muted);
  letter-spacing: 0.02em;
}

.points-display--empty {
  --points-accent: 154, 160, 154;
  --points-ink: var(--color-muted);
  opacity: 0.76;
}

@media (max-width: 640px) {
  .points-display {
    min-height: 34px;
    padding-right: 8px;
  }

  .coin-icon {
    width: 24px;
    height: 24px;
  }

  .points-label {
    display: none;
  }
}
</style>
