/**
 * Drown Platform — ambient ocean visualization
 * Canvas: water gradient, surface ripples, subtle splashes
 * SVG/HTML layers handled in template + CSS
 */
const Ocean = (() => {
    const SURFACE_RATIO = 0.09;
    const SPLASH_INTERVAL_MIN = 9000;
    const SPLASH_INTERVAL_MAX = 18000;

    let container, canvas, ctx, whaleLayer;
    let width = 0;
    let height = 0;
    let surfaceY = 0;
    let time = 0;
    let splashes = [];
    let splashTimer = 0;
    let nextSplashIn = 12000;
    let rafId = null;

    function init(options) {
        container = options.container;
        canvas = options.canvas;
        whaleLayer = options.whale;
        if (!container || !canvas) return;

        ctx = canvas.getContext('2d');
        resize();
        window.addEventListener('resize', resize);
        nextSplashIn = randomRange(SPLASH_INTERVAL_MIN, SPLASH_INTERVAL_MAX);
        rafId = requestAnimationFrame(tick);
    }

    function resize() {
        const rect = container.getBoundingClientRect();
        width = rect.width;
        height = rect.height;
        const dpr = Math.min(window.devicePixelRatio || 1, 2);
        canvas.width = width * dpr;
        canvas.height = height * dpr;
        canvas.style.width = `${width}px`;
        canvas.style.height = `${height}px`;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        surfaceY = height * SURFACE_RATIO;
    }

    function randomRange(min, max) {
        return min + Math.random() * (max - min);
    }

    function drawBackground() {
        const grad = ctx.createLinearGradient(0, 0, 0, height);
        grad.addColorStop(0, '#5ba4c9');
        grad.addColorStop(SURFACE_RATIO, '#2a8fae');
        grad.addColorStop(0.25, '#1a6b8a');
        grad.addColorStop(0.55, '#0f4a66');
        grad.addColorStop(1, '#061e2e');
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, width, height);
    }

    function drawSurface() {
        ctx.save();
        ctx.beginPath();
        ctx.moveTo(0, surfaceY);

        const segments = Math.ceil(width / 40) + 2;
        for (let i = 0; i <= segments; i++) {
            const x = (i / segments) * width;
            const wave = Math.sin(x * 0.012 + time * 0.0012) * 3
                + Math.sin(x * 0.025 + time * 0.0008) * 1.5;
            ctx.lineTo(x, surfaceY + wave);
        }

        ctx.lineTo(width, 0);
        ctx.lineTo(0, 0);
        ctx.closePath();

        const skyGrad = ctx.createLinearGradient(0, 0, 0, surfaceY + 8);
        skyGrad.addColorStop(0, '#a8d4ea');
        skyGrad.addColorStop(1, 'rgba(168, 212, 234, 0.35)');
        ctx.fillStyle = skyGrad;
        ctx.fill();

        ctx.strokeStyle = 'rgba(255, 255, 255, 0.25)';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(0, surfaceY);
        for (let i = 0; i <= segments; i++) {
            const x = (i / segments) * width;
            const wave = Math.sin(x * 0.012 + time * 0.0012) * 3
                + Math.sin(x * 0.025 + time * 0.0008) * 1.5;
            ctx.lineTo(x, surfaceY + wave);
        }
        ctx.stroke();
        ctx.restore();
    }

    function drawCaustics() {
        ctx.save();
        ctx.globalCompositeOperation = 'soft-light';
        ctx.globalAlpha = 0.08;

        const rows = 6;
        for (let row = 0; row < rows; row++) {
            const yBase = surfaceY + 40 + row * ((height - surfaceY) / rows);
            ctx.beginPath();
            for (let x = 0; x <= width; x += 8) {
                const y = yBase + Math.sin(x * 0.018 + time * 0.0006 + row) * 6
                    + Math.cos(x * 0.008 - time * 0.0004) * 4;
                if (x === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            }
            ctx.strokeStyle = `rgba(120, 220, 255, ${0.3 - row * 0.03})`;
            ctx.lineWidth = 2;
            ctx.stroke();
        }
        ctx.restore();
    }

    function drawSplashes() {
        for (let i = splashes.length - 1; i >= 0; i--) {
            const s = splashes[i];
            s.life += 1;
            s.y -= s.vy;
            s.vy *= 0.96;
            s.radius += 0.15;
            s.alpha -= 0.018;

            if (s.alpha <= 0) {
                splashes.splice(i, 1);
                continue;
            }

            ctx.beginPath();
            ctx.arc(s.x, s.y, s.radius, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(255, 255, 255, ${s.alpha * 0.6})`;
            ctx.fill();
        }
    }

    function spawnSplash(x, y) {
        const count = 2 + Math.floor(Math.random() * 2);
        for (let i = 0; i < count; i++) {
            splashes.push({
                x: x + randomRange(-8, 8),
                y: y + randomRange(-2, 2),
                radius: randomRange(1, 2.5),
                vy: randomRange(0.3, 1.2),
                alpha: randomRange(0.4, 0.7),
                life: 0,
            });
        }
    }

    function getWhalePosition() {
        if (!whaleLayer) return null;
        const rect = whaleLayer.getBoundingClientRect();
        const containerRect = container.getBoundingClientRect();
        return {
            x: rect.left - containerRect.left + rect.width * 0.15,
            y: rect.top - containerRect.top + rect.height * 0.6,
        };
    }

    function maybeSpawnSplash() {
        splashTimer += 16;
        if (splashTimer < nextSplashIn) return;
        splashTimer = 0;
        nextSplashIn = randomRange(SPLASH_INTERVAL_MIN, SPLASH_INTERVAL_MAX);

        const roll = Math.random();
        if (roll < 0.6) {
            const pos = getWhalePosition();
            if (pos) spawnSplash(pos.x, pos.y);
        } else {
            const bubbles = container.querySelectorAll('.app-bubble-wrap');
            if (bubbles.length === 0) return;
            const nearSurface = Array.from(bubbles).filter((el) => {
                const top = parseFloat(el.style.top) || 0;
                return top < surfaceY + 60;
            });
            const pool = nearSurface.length ? nearSurface : bubbles;
            const target = pool[Math.floor(Math.random() * pool.length)];
            const rect = target.getBoundingClientRect();
            const containerRect = container.getBoundingClientRect();
            spawnSplash(
                rect.left - containerRect.left + rect.width / 2,
                rect.top - containerRect.top
            );
        }
    }

    function tick() {
        time += 16;
        drawBackground();
        drawCaustics();
        drawSurface();
        drawSplashes();
        maybeSpawnSplash();
        rafId = requestAnimationFrame(tick);
    }

    function destroy() {
        if (rafId) cancelAnimationFrame(rafId);
        window.removeEventListener('resize', resize);
    }

    return { init, destroy };
})();
