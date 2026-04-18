// async function loadScrabData(date) {
//     try {
//         const response = await fetch("${API_CONFIG.NODE_API}/get-date", {
//             method: "POST",
//             headers: { "Content-Type": "application/json" },
//             body: JSON.stringify({ date: date })
//         });

//         if (!response.ok) throw new Error("Failed to fetch dashboard data");

//         const data = await response.json();

//         // 철강 스크랩(금일) 업데이트
//         const todayScrapCountElement = document.getElementById("todayScrapCount");
//         todayScrapCountElement.textContent = `${data.today_scrap_count || 0}`;  // 받아온 값 출력

//     } catch (error) {
//         console.error("Error loading dashboard data:", error);
//         alert("Failed to load scrab data.");
//     }
// }

// document.addEventListener("DOMContentLoaded", () => {
//     const datePicker = document.getElementById("dashboard_datePicker");

//     // 오늘 날짜를 동적으로 가져오기
//     const today = '2023-12-01';
//     console.log("Today is:", today); // 디버깅용 로그
//     datePicker.value = today;

//     // 초기화: 오늘 날짜로 데이터 로드
//     loadScrabData(today);

//     // 날짜 선택 이벤트 리스너 추가
//     datePicker.addEventListener("change", () => {
//         const selectedDate = datePicker.value;
//         console.log("Selected date:", selectedDate); // 디버깅용 로그
//         loadScrabData(selectedDate);
//     });
// });
async function loadScrabData(date) {
    try {
        const response = await fetch("${API_CONFIG.NODE_API}/get-date", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ date: date })
        });

        if (!response.ok) throw new Error("Failed to fetch dashboard data");

        const data = await response.json();

        // 철강 스크랩(금일) 업데이트
        const todayScrapCountElement = document.getElementById("todayScrapCount");
        todayScrapCountElement.textContent = `${data.today_scrap_count || 0}`; // 받아온 값 출력
        console.log("Scrap data loaded for date:", date); // 디버깅용 로그
    } catch (error) {
        console.error("Error loading dashboard data:", error);
        alert("Failed to load scrab data.");
    }
}

async function initializeDatePicker() {
    try {
        // 서버에서 엑셀 데이터의 마지막 날짜 가져오기
        const response = await fetch("${API_CONFIG.FLASK_API}/get-last-date");
        if (!response.ok) throw new Error("Failed to fetch last date");

        const data = await response.json();
        console.log("Last date fetched:", data); // 디버깅용 로그

        if (data.last_date) {
            const lastDate = data.last_date; // 마지막 날짜
            const datePicker = document.getElementById("dashboard_datePicker");

            // 날짜 선택기의 초기 값 설정
            datePicker.value = lastDate;

            // 초기화: 마지막 날짜로 데이터 로드
            await loadScrabData(lastDate); // 데이터를 정확히 로드하기 위해 await 추가

            // 날짜 선택 이벤트 리스너 추가
            datePicker.addEventListener("change", async () => {
                const selectedDate = datePicker.value;
                console.log("Selected date:", selectedDate); // 디버깅용 로그
                await loadScrabData(selectedDate);
            });
        } else {
            console.error("No last date found in the API response");
        }
    } catch (error) {
        console.error("Error initializing date picker:", error);
    }
}

document.addEventListener("DOMContentLoaded", async () => {
    await initializeDatePicker();
});

