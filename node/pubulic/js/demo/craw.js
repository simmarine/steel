function formatNumber(value, decimalPlaces = 0, useComma = true) {
    if (value == null || value === '-') return '-';
    const number = parseFloat(value);
    if (isNaN(number)) return '-';
    return useComma
        ? number.toFixed(decimalPlaces).replace(/\B(?=(\d{3})+(?!\d))/g, ',')
        : number.toFixed(decimalPlaces);
}

async function loadRecentData() {
    const response = await fetch('${API_CONFIG.FLASK_API}/get-recent-data');
    const data = await response.json();

    const recentDataBody = document.getElementById('recentDataBody');
    recentDataBody.innerHTML = '';

    if (data.recent) {
        // 날짜순으로 정렬 (오름차순: 오래된 날짜가 위로)
        const sortedData = data.recent.sort((a, b) => new Date(a.일자) - new Date(b.일자));

        sortedData.forEach(row => {
            // 날짜를 YYYY-MM-DD 형식으로 변환
            const formattedDate = new Date(row.일자).toISOString().split('T')[0];

            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${formattedDate || '-'}</td>
                <td>${row.중A || '-'}</td>
                <td>${row.중A_특 || '-'}</td>
                <td>${formatNumber(row.입고량, 1) || '-'}</td> <!-- 소수점 한자리 -->
                <td>${formatNumber(row.재고량, 0) || '-'}</td> <!-- 소수점 없이 컴마 -->
                <td>${formatNumber(row.입고율, 2) || '-'}</td> <!-- 소수점 두자리 -->
                <td>${formatNumber(row.제강생산량, 1) || '-'}</td> <!-- 소수점 한자리 -->
                <td>${formatNumber(row.고철투입량, 1) || '-'}</td> <!-- 소수점 한자리 -->
            `;
            recentDataBody.appendChild(tr);
        });
    } else {
        recentDataBody.innerHTML = '<tr><td colspan="8">데이터가 없습니다.</td></tr>';
    }
}

document.addEventListener('DOMContentLoaded', function () {
    loadRecentData();

    // ✅ 기본 요청 함수 (단일 작업용 - 리로드 포함)
    async function handleRequest(url, method='POST', body={}) {
        showSpinner();
        try {
            const response = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });

            const result = await response.json();
            hideSpinner();

            if (response.ok) {
                alert(result.message || 'Operation completed successfully!');
                window.location.reload();
            } else {
                alert(result.error || 'Error occurred during operation.');
            }
        } catch (error) {
            console.error('Error:', error);
            document.getElementById('responseMessage').innerText = 'Network error occurred!';
            hideSpinner();
        }
    }

    // ✅ 순차 작업용 요청 함수 (페이지 리로드 없이)
    async function basicRequest(url, method = 'POST', body = {}) {
        showSpinner();
        try {
            const response = await fetch(url, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });

            const result = await response.json();
            hideSpinner();

            if (!response.ok) {
                alert(result.error || 'Error occurred during operation.');
                throw new Error(result.error);
            }

            return result;
        } catch (error) {
            console.error(`Error in request to ${url}:`, error);
            hideSpinner();
            throw error;
        }
    }

    // ✅ 순차 작업 실행 함수
    const runAllTasks = async () => {
        try {
            // ✅ 1. 크롤링 실행
            await basicRequest('${API_CONFIG.FLASK_API}/run-crawling', 'POST', {
                start_date: '20250101',
                end_date: '20251231'
            });
            document.getElementById('taskResult').innerText = '✅ 크롤링 완료';

            // ✅ 2. 보간 실행
            await basicRequest('${API_CONFIG.FLASK_API}/interpolate-data');
            document.getElementById('taskResult').innerText = '✅ 보간 완료';

            // ✅ 3. 모델 업데이트 실행
            await basicRequest('${API_CONFIG.FLASK_API}/run-all-versions');
            document.getElementById('taskResult').innerText = '✅ 예측값 업데이트 완료';

            // ✅ 날짜 저장 요청
            const res = await fetch('${API_CONFIG.FLASK_API}/save-time', { method: 'POST' });
            const data = await res.json();
            document.getElementById('lastUpdate').innerText = `최근 업데이트 일자: ${data.date}`;

        } catch (err) {
            console.error('작업 중 오류 발생:', err);
            document.getElementById('taskResult').innerText = '❌ 작업 중 오류가 발생했습니다.';
        }
    };

    // 🔘 단일 업데이트 버튼 클릭 이벤트 연결
    document.getElementById('singleUpdateButton').addEventListener('click', runAllTasks);

    // ✅ 페이지 로드시 최근 업데이트 일자 불러오기
    fetch('${API_CONFIG.FLASK_API}/get-time')
        .then(res => res.json())
        .then(data => {
            document.getElementById('lastUpdate').innerText = `최근 업데이트 일자: ${data.lastUpdate}`;
        })
        .catch(err => {
            console.error('시간 로드 실패:', err);
        });

    // ✅ 다운로드 버튼 이벤트 연결
    const downloadPriceButton = document.getElementById('downloadPriceButton');
    downloadPriceButton?.addEventListener('click', () => {
        window.location.href = '${API_CONFIG.FLASK_API}/download-data-file';
    });

    const downloadSpecialPriceButton = document.getElementById('downloadSpecialPriceButton');
    downloadSpecialPriceButton?.addEventListener('click', () => {
        window.location.href = '${API_CONFIG.FLASK_API}/download-special-data-file';
    });
});

// ✅ 스피너 제어 함수
function showSpinner() {
    document.getElementById('loadingSpinner').classList.remove('d-none');
}
function hideSpinner() {
    document.getElementById('loadingSpinner').classList.add('d-none');
}

// 단가 및 특별구매단가 데이터 제출
document.getElementById('submitData').addEventListener('click', async () => {
    const formData = new FormData(document.getElementById('priceSpecialPriceForm'));
    const data = Object.fromEntries(formData.entries());

    // 숫자 필드를 숫자형으로 변환
    data.중A = data.중A ? parseFloat(data.중A) : null;
    data.중A_특 = data.중A_특 ? parseFloat(data.중A_특) : null;
    data.입고량 = parseFloat(data.입고량) || 0;
    data.재고량 = parseFloat(data.재고량) || 0;
    data.입고율 = parseFloat(data.입고율) || 0;
    data.제강생산량 = parseFloat(data.제강생산량) || 0;
    data.고철투입량 = parseFloat(data.고철투입량) || 0;


    showSpinner();
    try {
        const response = await fetch('${API_CONFIG.FLASK_API}/save-data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });

        const result = await response.json();
        hideSpinner();

        if (response.ok) {
            alert(result.message || 'Data saved successfully!');
            window.location.reload();
        } else {
            alert(result.error || 'Error occurred while saving data.');
        }
    } catch (error) {
        console.error('Error:', error);
        document.getElementById('responseMessage').innerText = 'Network error occurred!';
        hideSpinner();
    }
});

