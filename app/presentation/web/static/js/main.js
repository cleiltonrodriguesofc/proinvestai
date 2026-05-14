/**
 * ProInvestAI - Main JavaScript File
 */

document.addEventListener("DOMContentLoaded", () => {
    // Utility for showing/hiding elements with transitions
    const fadeOut = (el, duration = 300) => {
        el.style.opacity = 1;
        el.style.transition = `opacity ${duration}ms`;
        el.style.opacity = 0;
        setTimeout(() => {
            el.style.display = 'none';
        }, duration);
    };

    const fadeIn = (el, display = 'block', duration = 300) => {
        el.style.opacity = 0;
        el.style.display = display;
        el.style.transition = `opacity ${duration}ms`;
        setTimeout(() => {
            el.style.opacity = 1;
        }, 10);
    };

    // Make global utilities available
    window.ProInvestAI = {
        fadeOut,
        fadeIn,
        formatCurrency: (value) => {
            return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value);
        },
        formatPercent: (value) => {
            return new Intl.NumberFormat('pt-BR', { style: 'percent', minimumFractionDigits: 2 }).format(value);
        }
    };
});
