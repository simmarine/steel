let charts = [];
/**
 * 차트 데이터를 서버에서 불러오고 차트를 업데이트하는 함수
 * @param {string} fileName - 엑셀 파일 이름
 * @param {number} chartId - 차트 ID
 */
async function loadChartData(fileName, chartId) {
    const loadingSpinner = document.getElementById(`loadingSpinner${chartId}`);
    loadingSpinner.style.display = 'block';

    try {
        const response = await fetch('${API_CONFIG.FLASK_API}/get-chart-data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ file_name: fileName })
        });

        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        // 오차범위 설정
        let tolerance = 10; // 기본 오차범위
        if (fileName.includes('_30') || fileName.includes('_45')) {
            tolerance = 20;
        } else if (fileName.includes('_60')) {
            tolerance = 30;
        }

        // 오차범위 계산 (True Values 기준)
        const upperBound = data.true.map(value => value + tolerance);
        const lowerBound = data.true.map(value => value - tolerance);

        // 차트 데이터 업데이트
        const chart = charts[chartId];
        chart.data.labels = data.true.map((_, index) => index + 1); // x축: 인덱스
        chart.data.datasets[0].data = data.true; // True values
        chart.data.datasets[1].data = data.pred; // Predicted values
        chart.data.datasets[2].data = upperBound; // 상단 오차범위
        chart.data.datasets[3].data = lowerBound; // 하단 오차범위
        chart.update();
    } catch (error) {
        console.error(`Error loading chart data for ${fileName}:`, error);
        alert(`Failed to load data for ${fileName}`);
    } finally {
        loadingSpinner.style.display = 'none';
    }
}

/**
 * 차트를 생성하는 함수
 * @param {number} chartId - 차트 ID
 * @returns {Chart} - 생성된 차트 객체
 */
function createChart(chartId) {
    const ctx = document.getElementById(`chart${chartId}`).getContext('2d');
    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [], // 초기에는 빈 데이터
            datasets: [
                {
                    label: 'True Values',
                    data: [],
                    borderColor: 'blue',
                    fill: false
                },
                {
                    label: 'Predicted Values',
                    data: [],
                    borderColor: 'red',
                    fill: false
                },
                {
                    label: 'Upper Bound (+Tolerance)',
                    data: [],
                    borderColor: 'rgba(0, 128, 0, 0.3)',
                    fill: '-1',
                    backgroundColor: 'rgba(0, 128, 0, 0.1)',
                    borderWidth: 1,
                    borderDash: [5, 5]
                },
                {
                    label: 'Lower Bound (-Tolerance)',
                    data: [],
                    borderColor: 'rgba(0, 128, 0, 0.3)',
                    fill: '-1',
                    backgroundColor: 'rgba(0, 128, 0, 0.1)',
                    borderWidth: 1,
                    borderDash: [5, 5]
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false, // 화면 비율 유지 설정 해제
            plugins: {
                legend: {
                    position: 'top'
                },
                title: {
                    display: true,
                    text: 'True vs Predicted with Tolerance Range'
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Time Steps'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Values'
                    }
                }
            },
            layout: {
                padding: {
                    left: 10,
                    right: 10,
                    top: 10,
                    bottom: 10
                }
            }
        }
    });

    return chart;
}

// 초기화 함수
document.addEventListener('DOMContentLoaded', () => {
    const fileNames = [
        "2_10", "2_20", "2_30", "2_45", "2_60",
        "4_10", "4_20", "4_30", "4_45", "4_60"
    ];

    fileNames.forEach((fileName, index) => {
        charts.push(createChart(index)); // 차트 생성
        loadChartData(fileName, index); // 차트 데이터 로드
    });
});
