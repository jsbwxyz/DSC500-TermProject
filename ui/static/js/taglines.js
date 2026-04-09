/**
 * Rotating taglines for WigglNet branding
 */

class TaglineRotator {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.taglines = Array.from(this.container.querySelectorAll('.tagline'));
        this.currentIndex = 0;
        this.intervalId = null;

        this.start();
    }

    start() {
        this.intervalId = setInterval(() => {
            this.rotate();
        }, 3000); // Change every 3 seconds
    }

    rotate() {
        // Hide current
        this.taglines[this.currentIndex].classList.remove('active');

        // Move to next
        this.currentIndex = (this.currentIndex + 1) % this.taglines.length;

        // Show next
        this.taglines[this.currentIndex].classList.add('active');
    }

    stop() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const rotator = new TaglineRotator('taglines');
});
