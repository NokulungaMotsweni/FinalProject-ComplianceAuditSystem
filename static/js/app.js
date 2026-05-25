document.addEventListener("DOMContentLoaded", function () {
    // Chart
    const ctx = document.getElementById("riskChart");
    if (ctx) {
        new Chart(ctx, {
            type: "doughnut",
            data: {
                labels: ["Critical", "High", "Medium"],
                datasets: [{
                    data: [
                        parseInt(ctx.dataset.critical),
                        parseInt(ctx.dataset.high),
                        parseInt(ctx.dataset.medium)
                    ],
                    backgroundColor: [
                        "#e53e3e",
                        "#d97706",
                        "#0284c7"
                    ],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "65%",
                layout: {
                    padding: {
                        bottom: 10
                    }
                },
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: {
                            boxWidth: 12,
                            padding: 20,
                            font: {
                                size: 20
                            }
                        },
                        paddingTop: 60
                    },
                    tooltip: {
                        position: "nearest",
                        callbacks: {
                            label: function (context) {
                                return " " + context.label + ": " + context.parsed;
                            }
                        },
                        bodyFont: {
                            size: 15
                        },
                        padding: 10
                    }
                }
            }
        });
    }

    // Progress Donut
    const progressCanvas = document.getElementById("progressDonut");
    if (progressCanvas) {
        const pending = parseInt(progressCanvas.dataset.pending);
        const total = parseInt(progressCanvas.dataset.total);
        const reviewed = total - pending;

        new Chart(progressCanvas, {
            type: "doughnut",
            data: {
                datasets: [{
                    data: pending === 0 ? [total, 0] : [reviewed, pending],
                    backgroundColor: pending === 0
                        ? ["#16a34a", "#f0fdf4"]
                        : ["#e2e8f0", "#e53e3e"],
                    borderWidth: 0,
                }]
            },
            options: {
                cutout: "72%",
                plugins: { legend: { display: false }, tooltip: { enabled: false } },
                animation: { duration: 600 }
            }
        });
    }

    // Evaluation row click
    const evalRows = document.querySelectorAll('.eval-row');
    if (evalRows.length > 0) {
        const cards = {
            accuracy: document.getElementById('card-accuracy'),
            precision: document.getElementById('card-precision'),
            recall: document.getElementById('card-recall'),
            f1: document.getElementById('card-f1'),
        };

        evalRows.forEach(row => {
            row.addEventListener('click', () => {
                evalRows.forEach(r => r.classList.remove('eval-row-active'));
                row.classList.add('eval-row-active');

                cards.accuracy.textContent  = row.dataset.accuracy + '%';
                cards.precision.textContent = row.dataset.precision + '%';
                cards.recall.textContent    = row.dataset.recall + '%';
                cards.f1.textContent        = row.dataset.f1 + '%';
                document.getElementById('selected-method').textContent = row.querySelector('.method-label').textContent.trim();
            });
        });
    }
});