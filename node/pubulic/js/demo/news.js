// async function loadNewsData(date) {
//     try {
//         const response = await fetch("${API_CONFIG.NODE_API}/get-news", {
//             method: "POST",
//             headers: { "Content-Type": "application/json" },
//             body: JSON.stringify({ date: date })
//         });

//         if (!response.ok) throw new Error("Failed to fetch news data");

//         const data = await response.json();

//         // 뉴스 목록 업데이트
//         const newsListElement = document.querySelector(".news-list");
//         newsListElement.innerHTML = ''; // 기존 내용 초기화

//         if (data.news && data.news.length > 0) {
//             data.news.forEach(newsItem => {
//                 const newsElement = document.createElement("div");
//                 newsElement.classList.add("news-item", "d-flex", "align-items-center", "mb-3");

//                 const newsDateElement = document.createElement("div");
//                 newsDateElement.classList.add("news-date", "small", "text-gray-500", "mr-2");
//                 newsDateElement.textContent = newsItem.Date.slice(0, 10); // 'YYYY-MM-DD' 형식

//                 const newsTitleElement = document.createElement("div");
//                 newsTitleElement.classList.add("news-title");
//                 newsTitleElement.textContent = newsItem.Title;

//                 newsElement.appendChild(newsDateElement);
//                 newsElement.appendChild(newsTitleElement);

//                 newsListElement.appendChild(newsElement);
//             });
//         } else {
//             newsListElement.innerHTML = "<div class='no-news'>No news found for the selected date.</div>";
//         }

//     } catch (error) {
//         console.error("Error loading news data:", error);
//         alert("Failed to load news data.");
//     }
// }

// document.addEventListener("DOMContentLoaded", () => {
//     const datePicker = document.getElementById("dashboard_datePicker");

//     // 초기화: 오늘 날짜로 설정 및 데이터 로드
//     const today = '2023-12-01'; // 오늘 날짜를 YYYY-MM-DD 형식으로 설정
//     datePicker.value = today;
//     loadNewsData(today);

//     // 날짜 선택 이벤트 리스너 추가
//     datePicker.addEventListener("change", () => {
//         const selectedDate = datePicker.value;
//         loadNewsData(selectedDate); // 선택된 날짜로 뉴스 로드
//     });
// });
async function loadNewsData(date) {
    try {
        const response = await fetch("${API_CONFIG.NODE_API}/get-news", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ date: date })
        });

        if (!response.ok) throw new Error("Failed to fetch news data");

        const data = await response.json();

        // 뉴스 목록 업데이트
        const newsListElement = document.querySelector(".news-list");
        newsListElement.innerHTML = ''; // 기존 내용 초기화

        if (data.news && data.news.length > 0) {
            data.news.forEach(newsItem => {
                const newsElement = document.createElement("div");
                newsElement.classList.add("news-item", "d-flex", "align-items-center", "mb-3");

                const newsDateElement = document.createElement("div");
                newsDateElement.classList.add("news-date", "small", "text-gray-500", "mr-2");
                newsDateElement.textContent = newsItem.Date.slice(0, 10); // 'YYYY-MM-DD' 형식

                const newsTitleElement = document.createElement("div");
                newsTitleElement.classList.add("news-title");
                newsTitleElement.textContent = newsItem.Title;

                newsElement.appendChild(newsDateElement);
                newsElement.appendChild(newsTitleElement);

                newsListElement.appendChild(newsElement);
            });
        } else {
            newsListElement.innerHTML = "<div class='no-news'>No news found for the selected date.</div>";
        }

    } catch (error) {
        console.error("Error loading news data:", error);
        alert("Failed to load news data.");
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
            const lastDate = data.last_date; // 최신 날짜
            const datePicker = document.getElementById("dashboard_datePicker");

            // 날짜 선택기의 초기 값 설정
            datePicker.value = lastDate;

            // 최신 날짜로 뉴스 데이터 로드
            await loadNewsData(lastDate);

            // 날짜 선택 이벤트 리스너 추가
            datePicker.addEventListener("change", async () => {
                const selectedDate = datePicker.value;
                console.log("Selected date:", selectedDate); // 디버깅용 로그
                await loadNewsData(selectedDate);
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
