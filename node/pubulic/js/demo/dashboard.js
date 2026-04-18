// async function loadDashboardData(date) {
//     try {
//         const response = await fetch("${API_CONFIG.FLASK_API}/get-dashboard-data", {
//             method: "POST",
//             headers: { "Content-Type": "application/json" },
//             body: JSON.stringify({ date: date })
//         });

//         if (!response.ok) throw new Error("Failed to fetch dashboard data");

//         const data = await response.json();

//         // 데이터 업데이트
//         document.querySelector(".price-prediction").textContent = `${data.price} `;
//         document.querySelector(".special-price-prediction").textContent = `${data.special_price} `;
        
//         // 물동량을 ton으로 표시 (kg 대신 ton으로 출력)
//         const volumeValue = parseFloat(data.volume.split(" ")[0]); // kg 값만 추출
//         const volumeInTon = volumeValue.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + ' ton';
//         document.querySelector(".volume-prediction").textContent = volumeInTon;

//         // Progress bar 업데이트
//         const progressBar = document.querySelector(".progress-bar");
//         progressBar.style.width = `${Math.min((volumeValue / 5000) * 100, 100)}%`;
//         progressBar.setAttribute("aria-valuenow", volumeValue);

//     } catch (error) {
//         console.error("Error loading dashboard data:", error);
//         alert("Failed to load dashboard data.");
//     }
// }

// document.addEventListener("DOMContentLoaded", () => {
//     const datePicker = document.getElementById("dashboard_datePicker");

//     // 초기화: 오늘 날짜로 설정 및 데이터 로드
//     const today = '2025-01-01';
//     datePicker.value = today;
//     loadDashboardData(today);

//     // 날짜 선택 이벤트 리스너 추가
//     datePicker.addEventListener("change", () => {
//         const selectedDate = datePicker.value;
//         loadDashboardData(selectedDate);
//     });
// });
async function loadDashboardData(date) {
    try {
        const response = await fetch("${API_CONFIG.FLASK_API}/get-dashboard-data", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ date: date })
        });

        if (!response.ok) throw new Error("Failed to fetch dashboard data");

        const data = await response.json();

        // 데이터 업데이트
        document.querySelector(".price-prediction").textContent = `${data.price} `;
        document.querySelector(".special-price-prediction").textContent = `${data.special_price} `;

        // 물동량을 ton으로 표시 (kg 대신 ton으로 출력)
        const volumeValue = parseFloat(data.volume.split(" ")[0]); // kg 값만 추출
        const volumeInTon = volumeValue.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + ' ton';
        document.querySelector(".volume-prediction").textContent = volumeInTon;

        // Progress bar 업데이트
        const progressBar = document.querySelector(".progress-bar");
        progressBar.style.width = `${Math.min((volumeValue / 5000) * 100, 100)}%`;
        progressBar.setAttribute("aria-valuenow", volumeValue);

    } catch (error) {
        console.error("Error loading dashboard data:", error);
        alert("Failed to load dashboard data.");
    }
}

async function initializeDatePickerAndLoadDashboard() {
    try {
        // 서버에서 엑셀 데이터의 마지막 날짜 가져오기
        const response = await fetch("${API_CONFIG.FLASK_API}/get-last-date");
        if (!response.ok) throw new Error("Failed to fetch last date");

        const data = await response.json();
        console.log("Last date fetched:", data);

        if (data.last_date) {
            const lastDate = data.last_date;
            const datePicker = document.getElementById("dashboard_datePicker");

            // 날짜 선택기의 초기 값 설정
            datePicker.value = lastDate;

            // 초기화: 최신 날짜로 데이터 로드
            await loadDashboardData(lastDate);

            // 날짜 선택 이벤트 리스너 추가
            datePicker.addEventListener("change", async () => {
                const selectedDate = datePicker.value;
                console.log("Selected date:", selectedDate);
                await loadDashboardData(selectedDate);
            });
        } else {
            console.error("No last date found in the API response");
        }
    } catch (error) {
        console.error("Error initializing date picker:", error);
    }
}

document.addEventListener("DOMContentLoaded", async () => {
    await initializeDatePickerAndLoadDashboard();
});

