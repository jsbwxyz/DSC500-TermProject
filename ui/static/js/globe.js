/**
 * 3D Spinning Word Cloud Globe
 * Creates a rotating sphere of keywords projected onto a 2D canvas
 */

class WordGlobe {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.words = [];
        this.rotation = { x: 0, y: 0 };
        this.autoRotate = true;
        this.radius = 250;
        this.animationId = null;

        this.setupCanvas();
        this.loadWords();
        this.setupInteraction();
    }

    setupCanvas() {
        const dpr = window.devicePixelRatio || 1;
        const rect = this.canvas.getBoundingClientRect();

        this.canvas.width = rect.width * dpr;
        this.canvas.height = rect.height * dpr;
        this.ctx.scale(dpr, dpr);

        this.centerX = rect.width / 2;
        this.centerY = rect.height / 2;
    }

    async loadWords() {
        try {
            const response = await fetch('/wordcloud-data');
            const data = await response.json();
            this.initWords(data.keywords);
        } catch (error) {
            console.error('Error loading word cloud data:', error);
            // Fallback to default words
            this.initWords([
                { text: 'analytics', weight: 100 },
                { text: 'ecommerce', weight: 90 },
                { text: 'machine learning', weight: 85 },
                { text: 'predictions', weight: 80 },
                { text: 'market', weight: 75 },
                { text: 'data', weight: 70 },
                { text: 'trends', weight: 65 },
                { text: 'insights', weight: 60 },
                { text: 'sentiment', weight: 55 },
                { text: 'keywords', weight: 50 }
            ]);
        }
    }

    initWords(keywords) {
        // Distribute words evenly on a sphere using Fibonacci spiral
        const goldenAngle = Math.PI * (3 - Math.sqrt(5));

        this.words = keywords.map((word, i) => {
            const y = 1 - (i / (keywords.length - 1)) * 2;
            const radiusAtY = Math.sqrt(1 - y * y);
            const theta = goldenAngle * i;

            const x = Math.cos(theta) * radiusAtY;
            const z = Math.sin(theta) * radiusAtY;

            // Size based on weight
            const minSize = 12;
            const maxSize = 32;
            const normalizedWeight = word.weight / Math.max(...keywords.map(k => k.weight));
            const size = minSize + (maxSize - minSize) * normalizedWeight;

            return {
                text: word.text,
                x: x * this.radius,
                y: y * this.radius,
                z: z * this.radius,
                size: size,
                weight: word.weight,
                alpha: 1
            };
        });

        this.animate();
    }

    setupInteraction() {
        let isDragging = false;
        let lastX, lastY;

        this.canvas.addEventListener('mousedown', (e) => {
            isDragging = true;
            this.autoRotate = false;
            lastX = e.clientX;
            lastY = e.clientY;
        });

        this.canvas.addEventListener('mousemove', (e) => {
            if (isDragging) {
                const deltaX = e.clientX - lastX;
                const deltaY = e.clientY - lastY;

                this.rotation.y += deltaX * 0.01;
                this.rotation.x += deltaY * 0.01;

                lastX = e.clientX;
                lastY = e.clientY;
            }
        });

        this.canvas.addEventListener('mouseup', () => {
            isDragging = false;
            setTimeout(() => {
                this.autoRotate = true;
            }, 2000);
        });

        this.canvas.addEventListener('mouseleave', () => {
            isDragging = false;
        });
    }

    rotatePoint(x, y, z, rx, ry) {
        // Rotate around X axis
        let cos = Math.cos(rx);
        let sin = Math.sin(rx);
        let y1 = y * cos - z * sin;
        let z1 = y * sin + z * cos;

        // Rotate around Y axis
        cos = Math.cos(ry);
        sin = Math.sin(ry);
        let x1 = x * cos - z1 * sin;
        let z2 = x * sin + z1 * cos;

        return { x: x1, y: y1, z: z2 };
    }

    projectPoint(x, y, z) {
        // Perspective projection
        const fov = 500;
        const scale = fov / (fov + z);

        return {
            x: this.centerX + x * scale,
            y: this.centerY + y * scale,
            scale: scale
        };
    }

    animate() {
        if (this.autoRotate) {
            this.rotation.y += 0.003;
            this.rotation.x = Math.sin(Date.now() * 0.0003) * 0.1;
        }

        this.render();
        this.animationId = requestAnimationFrame(() => this.animate());
    }

    render() {
        // Clear canvas with fade effect
        this.ctx.fillStyle = 'rgba(250, 250, 248, 0.1)';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        // Transform and sort words by Z-depth
        const transformedWords = this.words.map(word => {
            const rotated = this.rotatePoint(
                word.x,
                word.y,
                word.z,
                this.rotation.x,
                this.rotation.y
            );
            const projected = this.projectPoint(rotated.x, rotated.y, rotated.z);

            return {
                ...word,
                px: projected.x,
                py: projected.y,
                scale: projected.scale,
                z: rotated.z
            };
        });

        // Sort by Z (back to front)
        transformedWords.sort((a, b) => a.z - b.z);

        // Draw words
        transformedWords.forEach(word => {
            // Calculate alpha based on Z position (far = dim, near = bright)
            const alpha = (word.z + this.radius) / (this.radius * 2);

            // Grayscale from light gray to black based on depth
            const lightness = 20 + alpha * 30; // 20% to 50% lightness

            this.ctx.save();
            this.ctx.translate(word.px, word.py);

            // Font
            const fontSize = word.size * word.scale;
            this.ctx.font = `600 ${fontSize}px 'IBM Plex Mono', monospace`;
            this.ctx.textAlign = 'center';
            this.ctx.textBaseline = 'middle';

            // Subtle glow effect
            this.ctx.shadowBlur = 8 * word.scale;
            this.ctx.shadowColor = `hsla(0, 0%, ${lightness}%, ${alpha * 0.3})`;

            // Text in grayscale (black to gray)
            this.ctx.fillStyle = `hsla(0, 0%, ${lightness}%, ${alpha * 0.9})`;
            this.ctx.fillText(word.text, 0, 0);

            this.ctx.restore();
        });
    }

    stop() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
    }
}

// Initialize globe when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const globe = new WordGlobe('wordGlobe');

    // Handle window resize
    let resizeTimeout;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(() => {
            globe.setupCanvas();
        }, 250);
    });
});
