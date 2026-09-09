"use strict";

function leadingZeroBits(bytes) {
  let bits = 0;
  for (const byte of bytes) {
    if (byte === 0) {
      bits += 8;
      continue;
    }
    let leading = 0;
    for (let i = 7; i >= 0; i -= 1) {
      if ((byte >> i) & 1) break;
      leading += 1;
    }
    bits += leading;
    break;
  }
  return bits;
}

self.onmessage = async (event) => {
  const { challenge, difficultyBits, requestId } = event.data;
  const encoder = new TextEncoder();
  let nonce = 0;

  while (true) {
    const attempt = String(nonce);
    const data = encoder.encode(challenge + attempt);
    const digest = new Uint8Array(await crypto.subtle.digest("SHA-256", data));
    if (leadingZeroBits(digest) >= difficultyBits) {
      self.postMessage({ requestId, done: true, nonce: attempt });
      return;
    }
    nonce += 1;
    if (nonce % 4000 === 0) {
      self.postMessage({ requestId, done: false, progress: nonce });
      // Yield briefly so this worker thread doesn't starve message delivery.
      await new Promise((resolve) => setTimeout(resolve, 0));
    }
  }
};
