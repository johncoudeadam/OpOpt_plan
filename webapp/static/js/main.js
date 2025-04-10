// Main JavaScript file for Rail Operations & Maintenance Optimizer

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Add event listeners to buttons
    const runOptimizationBtn = document.getElementById('run-optimization');
    const runFreshOptimizationBtn = document.getElementById('run-fresh-optimization');
    const regenerateDataBtn = document.getElementById('regenerate-data');
    const viewDataBtn = document.getElementById('view-data');

    if (runOptimizationBtn) {
        runOptimizationBtn.addEventListener('click', function() {
            // Call the runOptimization function from visualization.js with cached results
            if (typeof window.runOptimization === 'function') {
                window.runOptimization(true, false); // Use cached results, don't regenerate
            } else {
                console.error('runOptimization function not found');
                alert('Error: Optimization functionality not available');
            }
        });
    }

    if (runFreshOptimizationBtn) {
        runFreshOptimizationBtn.addEventListener('click', function() {
            // Call the runOptimization function without using cached results
            if (typeof window.runOptimization === 'function') {
                if (confirm('Running a fresh optimization may take several minutes. Continue?')) {
                    window.runOptimization(false, false); // Run a fresh optimization, don't regenerate
                }
            } else {
                console.error('runOptimization function not found');
                alert('Error: Optimization functionality not available');
            }
        });
    }

    if (regenerateDataBtn) {
        regenerateDataBtn.addEventListener('click', function() {
            // Call the runOptimization function with regenerate flag
            if (typeof window.runOptimization === 'function') {
                if (confirm('Regenerating data and running optimization may take several minutes. Continue?')) {
                    window.runOptimization(false, true); // Run optimization with regenerated data
                }
            } else {
                console.error('runOptimization function not found');
                alert('Error: Optimization functionality not available');
            }
        });
    }

    if (viewDataBtn) {
        viewDataBtn.addEventListener('click', function(e) {
            // Prevent default behavior for now to keep the user on the same page
            e.preventDefault();
            
            // Display message
            const resultContainer = document.getElementById('optimization-results');
            if (resultContainer) {
                resultContainer.innerHTML = '<div class="alert alert-info">Data view will be implemented in a future update.</div>';
            }
        });
    }

    // Add active class to current navigation item
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link');
    
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });

    // Auto-load the saved results when the page loads
    if (typeof window.runOptimization === 'function') {
        window.runOptimization(true, false);
    }
}); 