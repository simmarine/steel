// Chart.js 기본 설정
Chart.defaults.global.defaultFontFamily = 'Nunito', '-apple-system,system-ui,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif';
Chart.defaults.global.defaultFontColor = '#858796';

// 숫자 포맷 함수
function number_format(number, decimals, dec_point, thousands_sep) {
    number = (number + '').replace(',', '').replace(' ', '');
    var n = !isFinite(+number) ? 0 : +number,
        prec = !isFinite(+decimals) ? 0 : Math.abs(decimals),
        sep = (typeof thousands_sep === 'undefined') ? ',' : thousands_sep,
        dec = (typeof dec_point === 'undefined') ? '.' : dec_point,
        s = '',
        toFixedFix = function(n, prec) {
            var k = Math.pow(10, prec);
            return '' + Math.round(n * k) / k;
        };
    s = (prec ? toFixedFix(n, prec) : '' + Math.round(n)).split('.');
    if (s[0].length > 3) {
        s[0] = s[0].replace(/\B(?=(?:\d{3})+(?!\d))/g, sep);
    }
    if ((s[1] || '').length < prec) {
        s[1] = s[1] || '';
        s[1] += new Array(prec - s[1].length + 1).join('0');
    }
    return s.join(dec);
}

// 차트 초기화 함수
function initializeChart(context, label, color, yTitle, labels) {
    return new Chart(context, {
        type: 'line',
        data: {
            labels: labels, // 차트 레이블
            datasets: [{
                label: label,
                lineTension: 0.3,
                backgroundColor: color.background,
                borderColor: color.border,
                pointRadius: 3,
                pointBackgroundColor: color.border,
                pointBorderColor: color.border,
                pointHoverRadius: 3,
                pointHoverBackgroundColor: color.border,
                pointHoverBorderColor: color.border,
                pointHitRadius: 10,
                pointBorderWidth: 2,
                data: []
            }]
        },
        options: {
            maintainAspectRatio: false,
            layout: {
                padding: {
                    left: 10,
                    right: 25,
                    top: 25,
                    bottom: 0
                }
            },
            scales: {
                xAxes: [{
                    time: { unit: 'date' },
                    gridLines: { display: false, drawBorder: false },
                    ticks: { maxTicksLimit: 7 }
                }],
                yAxes: [{
                    ticks: {
                        maxTicksLimit: 5,
                        padding: 10,
                        callback: function(value) {
                            return value;
                            // return number_format(value) + '₩';
                        }
                    },
                    gridLines: {
                        color: "rgb(234, 236, 244)",
                        zeroLineColor: "rgb(234, 236, 244)",
                        drawBorder: false,
                        borderDash: [2],
                        zeroLineBorderDash: [2]
                    }
                }]
            },
            legend: { display: false },
            tooltips: {
                backgroundColor: "rgb(255,255,255)",
                bodyFontColor: "#858796",
                titleMarginBottom: 10,
                titleFontColor: '#6e707e',
                titleFontSize: 14,
                borderColor: '#dddfeb',
                borderWidth: 1,
                xPadding: 15,
                yPadding: 15,
                displayColors: false,
                intersect: false,
                mode: 'index',
                caretPadding: 10,
                callbacks: {
                    label: function(tooltipItem, chart) {
                        var datasetLabel = chart.datasets[tooltipItem.datasetIndex].label || '';
                        
                        // 물동량의 단위를 ton으로 표시
                        if (datasetLabel === '물동량') {
                            return datasetLabel + ': ' + 
                                tooltipItem.yLabel.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 3 }) + ' ton';
                        } else {
                            return datasetLabel + ': ' + 
                                tooltipItem.yLabel.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 2 }) + ' 원';
                        }
                    }
                }
            }
            
            
        }
    });
}
// 전역 변수 선언
let priceChart, specialPriceChart, volumeChart;

document.addEventListener('DOMContentLoaded', function () {
    const ctxPrice = document.getElementById('dashboard_priceChart').getContext('2d');
    const ctxSpecial = document.getElementById('dashboard_specialPriceChart').getContext('2d');
    const ctxVolume = document.getElementById('dashboard_volumeChart').getContext('2d');

    // 차트 생성
    priceChart = initializeChart(ctxPrice, '단가', { background: 'rgba(78, 115, 223, 0.05)', border: 'rgba(78, 115, 223, 1)' }, '단가 (원)', ["10일", "20일", "30일", "45일", "60일"]);
    specialPriceChart = initializeChart(ctxSpecial, '특별구매단가', { background: 'rgba(28, 200, 138, 0.05)', border: 'rgba(28, 200, 138, 1)' }, '특별구매단가 (원)', ["10일", "20일", "30일", "45일", "60일"]);
    volumeChart = initializeChart(ctxVolume, '물동량', { background: 'rgba(54, 185, 204, 0.05)', border: 'rgba(54, 185, 204, 1)' }, '물동량', ["10일", "20일", "30일"]); // 30일까지만 표시

    initializeDatePickerAndLoadData(); // 날짜 초기화 및 데이터 로드
});
async function initializeDatePickerAndLoadData() {
    try {
        const response = await fetch("http://203.253.181.161:5050/get-last-date");
        if (!response.ok) throw new Error("Failed to fetch last date");

        const data = await response.json();
        console.log("Last date fetched:", data);

        if (data.last_date) {
            const lastDate = data.last_date;
            const datePicker = document.getElementById("dashboard_datePicker");

            datePicker.value = lastDate;

            // 데이터 로드
            await loadScrabData(lastDate);
            await handlePriceDateChange(lastDate);

            // 날짜 선택 이벤트 등록
            datePicker.addEventListener("change", async () => {
                const selectedDate = datePicker.value;
                console.log("Selected date:", selectedDate);
                await loadScrabData(selectedDate);
                await handlePriceDateChange(selectedDate);
            });
        } else {
            console.error("No last date found in the API response");
        }
    } catch (error) {
        console.error("Error initializing date picker:", error);
    }
}
// 날짜에 특정 일수를 더해 반환하는 함수
function addDaysToDate(baseDate, days) {
    const newDate = new Date(baseDate); // 기준 날짜를 Date 객체로 변환
    newDate.setDate(newDate.getDate() + days); // days를 더함
    return newDate.toISOString().split('T')[0]; // YYYY-MM-DD 형식으로 반환
}
async function handlePriceDateChange(date) {
    const loadingSpinner = document.getElementById('loadingSpinner');
    if (loadingSpinner) loadingSpinner.style.display = 'block';

    try {
        console.log(`Fetching dashboard data for date: ${date}`);
        const dashboardResponse = await fetch('http://203.253.181.161:5050/get-dashboard-data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date }),
        });

        if (!dashboardResponse.ok) throw new Error(`HTTP error! status: ${dashboardResponse.status}`);
        const dashboardData = await dashboardResponse.json();
        console.log("Dashboard data fetched:", dashboardData);

        const selectedPrice = parseFloat(dashboardData.price.replace(' 원', '').replace(',', ''));
        const selectedSpecialPrice = parseFloat(dashboardData.special_price.replace(' 원', '').replace(',', ''));
        const selectedVolume = parseFloat(dashboardData.volume.replace(' kg', '').replace(',', ''));

        console.log("Parsed values:", { selectedPrice, selectedSpecialPrice, selectedVolume });

        // Price 데이터 업데이트
        const priceModelKeys = ['2_10', '2_20', '2_30', '2_45', '2_60'];
        const pricePredictions = [selectedPrice];
        const predictionOffsets = [0, 10, 20, 30, 45, 60];
        const priceLabels = predictionOffsets.map(offset => addDaysToDate(date, offset));
        
        for (const modelKey of priceModelKeys) {
            const response = await fetch('http://203.253.181.161:5050/get-model-prediction', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model_key: modelKey, date }),
            });
            const data = await response.json();
            pricePredictions.push(data.pred !== undefined ? data.pred : null);
        }

        const specialPriceModelKeys = ['4_10', '4_20', '4_30', '4_45', '4_60'];
        const specialPricePredictions = [selectedSpecialPrice];
        const specialPriceLabels = predictionOffsets.map(offset => addDaysToDate(date, offset));

        for (const modelKey of specialPriceModelKeys) {
            const response = await fetch('http://203.253.181.161:5050/get-model-prediction', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model_key: modelKey, date }),
            });
            const data = await response.json();
            specialPricePredictions.push(data.pred !== undefined ? data.pred : null);
        }

        console.log("Price and Special Price predictions fetched.");

        // 물동량 데이터 업데이트
        const volumeLabels = [date, addDaysToDate(date, 10), addDaysToDate(date, 20), addDaysToDate(date, 30)];
        const volumePredictions = [selectedVolume];

        try {
            const volumeResponse = await fetch('http://203.253.181.161:5050/transfer-predict', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ date })
            });

            if (!volumeResponse.ok) throw new Error(`Error fetching volume predictions`);
            const volumeData = await volumeResponse.json();
            ["10", "20", "30"].forEach((key, index) => {
                const prediction = parseFloat(volumeData.volume[key]);
                if (!isNaN(prediction)) {
                    volumePredictions[index + 1] = prediction; // 기존 값 유지 후 새 데이터 업데이트
                }
            });
        } catch (error) {
            console.error('Error fetching volume data:', error);
        }

        console.log("Final predictions:", { pricePredictions, specialPricePredictions, volumePredictions });

        // 차트 업데이트
        priceChart.data.labels = priceLabels;
        priceChart.data.datasets[0].data = pricePredictions;
        specialPriceChart.data.labels = specialPriceLabels;
        specialPriceChart.data.datasets[0].data = specialPricePredictions;
        volumeChart.data.labels = volumeLabels;
        volumeChart.data.datasets[0].data = volumePredictions;

        priceChart.update();
        specialPriceChart.update();
        volumeChart.update();

    } catch (error) {
        console.error('Error fetching data:', error);
    } finally {
        if (loadingSpinner) loadingSpinner.style.display = 'none';
    }
}



async function initializeDatePickerAndLoadData() {
    try {
        // 서버에서 엑셀 데이터의 마지막 날짜 가져오기
        const response = await fetch("http://203.253.181.161:5050/get-last-date");
        if (!response.ok) throw new Error("Failed to fetch last date");

        const data = await response.json();
        console.log("Last date fetched:", data); // 디버깅용 로그

        if (data.last_date) {
            const lastDate = data.last_date; // 마지막 날짜
            const datePicker = document.getElementById("dashboard_datePicker");

            // 날짜 선택기의 초기 값 설정
            datePicker.value = lastDate;

            // 초기화: 마지막 날짜로 데이터 로드
            await loadScrabData(lastDate);
            await handlePriceDateChange(lastDate); // 모델 예측값 로드

            // 날짜 선택 이벤트 리스너 추가
            datePicker.addEventListener("change", async () => {
                const selectedDate = datePicker.value;
                console.log("Selected date:", selectedDate); // 디버깅용 로그
                await loadScrabData(selectedDate); // 스크랩 데이터 로드
                await handlePriceDateChange(selectedDate); // 모델 예측값 로드
            });
        } else {
            console.error("No last date found in the API response");
        }
    } catch (error) {
        console.error("Error initializing date picker:", error);
    }
}

document.addEventListener("DOMContentLoaded", async () => {
    await initializeDatePickerAndLoadData();
});

// });


