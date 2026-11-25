let fixed = null;

export function setLatency(ms) {
  fixed = ms == null ? null : Number(ms);
}

export function wait() {
  const ms = fixed == null ? 200 + Math.floor(Math.random() * 400) : fixed;
  return new Promise((resolve) => setTimeout(resolve, ms));
}
