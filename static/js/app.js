console.log("app.js updated - doughnut");
document.addEventListener("DOMContentLoaded", function () {
    const ctx = document.getElementById("riskChart");

    if (!ctx) return; // prevents errors on other pages

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
                "#e53e3e",  // critical - matches CSS
                "#d97706",  // high - matches CSS
                "#0284c7"   // medium - matches CSS
            ],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: "65%",
            plugins: {
                legend: {
                    position: "bottom"
                }
            }

        }
    });
});