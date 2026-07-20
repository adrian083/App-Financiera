/**
 * Tutorial de bienvenida — slider paso a paso.
 */
(function () {
    let currentStep = 0;
    const totalSteps = 4;

    function getSteps() {
        return document.querySelectorAll('[data-tutorial-step]');
    }

    function getDots() {
        return document.querySelectorAll('[data-tutorial-dot]');
    }

    function showStep(index) {
        currentStep = Math.max(0, Math.min(index, totalSteps - 1));
        getSteps().forEach((step, i) => {
            step.classList.toggle('hidden', i !== currentStep);
        });
        getDots().forEach((dot, i) => {
            dot.classList.toggle('bg-primary-600', i === currentStep);
            dot.classList.toggle('bg-slate-300', i !== currentStep);
            dot.classList.toggle('dark:bg-slate-600', i !== currentStep);
        });
        const prevBtn = document.getElementById('tutorial-prev');
        const nextBtn = document.getElementById('tutorial-next');
        const finishBtn = document.getElementById('tutorial-finish');
        if (prevBtn) prevBtn.classList.toggle('invisible', currentStep === 0);
        if (nextBtn) nextBtn.classList.toggle('hidden', currentStep === totalSteps - 1);
        if (finishBtn) finishBtn.classList.toggle('hidden', currentStep !== totalSteps - 1);
    }

    window.tutorialNext = function () {
        if (currentStep < totalSteps - 1) showStep(currentStep + 1);
    };

    window.tutorialPrev = function () {
        if (currentStep > 0) showStep(currentStep - 1);
    };

    window.initTutorial = function () {
        const modal = document.getElementById('tutorial-modal');
        if (!modal) return;
        showStep(0);
    };

    window.completarTutorial = async function () {
        const csrf = document.querySelector('#tutorial-csrf [name=csrfmiddlewaretoken]')?.value;
        try {
            await fetch('/tutorial/completar/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrf,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({}),
            });
        } catch (e) { /* silencioso */ }
        const modal = document.getElementById('tutorial-modal');
        if (modal) {
            modal.classList.add('hidden');
            modal.classList.remove('flex');
        }
    };
})();
