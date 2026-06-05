<template>
  <div class="points-display">
    <svg class="coin-icon" width="18" height="18" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.5" />
      <circle cx="12" cy="12" r="6" stroke="currentColor" stroke-width="1.5" stroke-dasharray="2 3" />
      <text x="12" y="16" text-anchor="middle" font-size="8" fill="currentColor" font-weight="700">¥</text>
    </svg>
    <span class="points-value">{{ balance }}</span>
  </div>
</template>

<script setup>
defineProps({
  balance: {
    type: Number,
    default: 0
  }
})
</script>

<style scoped>
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
</style>
