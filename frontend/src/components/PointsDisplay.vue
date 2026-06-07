<template>
  <div class="points-group">
    <div class="points-display" :class="{ 'points-free': free }">
      <svg class="coin-icon" width="18" height="18" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.5" />
        <circle cx="12" cy="12" r="6" stroke="currentColor" stroke-width="1.5" stroke-dasharray="2 3" />
        <text x="12" y="16" text-anchor="middle" font-size="8" fill="currentColor" font-weight="700">{{ free ? '免' : '¥' }}</text>
      </svg>
      <span class="points-value">{{ balance }}</span>
      <span v-if="free" class="points-label">免费</span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  balance: {
    type: Number,
    default: 0
  },
  free: {
    type: Boolean,
    default: false
  }
})
</script>

<style scoped>
.points-group {
  display: flex;
  align-items: center;
}

.points-display {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-radius: 20px;
  background: rgba(120, 140, 93, 0.1);
  border: 1px solid rgba(120, 140, 93, 0.2);
  position: relative;
  overflow: hidden;
}

.points-free {
  background: rgba(106, 155, 204, 0.1);
  border-color: rgba(106, 155, 204, 0.2);
}

.points-free .coin-icon {
  color: var(--color-blue);
  animation: none;
}

.points-free .points-value {
  color: var(--color-blue);
}

.points-display::after {
  content: '';
  position: absolute;
  top: -50%;
  left: -60%;
  width: 40%;
  height: 200%;
  background: linear-gradient(105deg, transparent 40%, rgba(120, 140, 93, 0.12) 45%, transparent 50%);
  animation: coin-shine 3s ease-in-out infinite;
  pointer-events: none;
}

.points-free::after {
  background: linear-gradient(105deg, transparent 40%, rgba(106, 155, 204, 0.12) 45%, transparent 50%);
}

@keyframes coin-shine {
  0%, 100% { transform: translateX(-100%); }
  50% { transform: translateX(400%); }
}

.coin-icon {
  color: var(--color-green);
  animation: coin-bounce 2s ease-in-out infinite;
}

@keyframes coin-bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-2px); }
}

.points-value {
  font-family: var(--font-heading);
  font-size: 14px;
  font-weight: 700;
  color: var(--color-green);
  letter-spacing: -0.02em;
}

.points-label {
  font-family: var(--font-heading);
  font-size: 10px;
  font-weight: 600;
  color: var(--color-blue);
  opacity: 0.7;
  letter-spacing: 0.04em;
}
</style>
