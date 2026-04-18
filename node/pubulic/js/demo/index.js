/**
 * index.js  ─  대시보드 메인 로직
 *
 * 차트 구성:
 *   A) dashboard_directionChart  : 가격 추이 + 예측 포인트 (방향성 라인 차트)
 *   B) dashboard_probChart       : 10/30/60일 상승 확률 수평 바 차트
 */

/* ── Chart.js 전역 기본값 ── */
Chart.defaults.global.defaultFontFamily =
    'Nunito, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
Chart.defaults.global.defaultFontColor = '#858796';

/* ── 유틸 ── */
function fmt(n, dec = 1) {
    if (n == null || isNaN(n)) return '--';
    return Number(n).toLocaleString('ko-KR', {
        minimumFractionDigits: dec,
        maximumFractionDigits: dec
    });
}
function addDays(dateStr, days) {
    const d = new Date(dateStr);
    d.setDate(d.getDate() + days);
    return d.toISOString().split('T')[0];
}
function shortDate(dateStr) {
    if (!dateStr) return '';
    return dateStr.slice(5); // MM-DD
}

/* ── 전역 차트 인스턴스 ── */
let directionChart = null;
let probChart      = null;


/* ============================================================
   차트 A : 가격 방향성 라인 차트
   ============================================================ */
function buildDirectionChart(ctx) {
    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                /* 0: 실제 가격 (과거) */
                {
                    label: '실제 시장단가',
                    data: [],
                    borderColor: 'rgba(58, 134, 200, 0.9)',
                    backgroundColor: 'rgba(58, 134, 200, 0.06)',
                    borderWidth: 2,
                    pointRadius: 2,
                    pointHoverRadius: 4,
                    lineTension: 0.3,
                    fill: true,
                    borderDash: [],
                },
                /* 1: 예측 라인 (기준→10d→30d→60d) */
                {
                    label: 'AI 예측 방향',
                    data: [],
                    borderColor: 'rgba(28, 200, 138, 1)',
                    backgroundColor: 'rgba(28, 200, 138, 0.08)',
                    borderWidth: 2.5,
                    pointRadius: 7,
                    pointHoverRadius: 9,
                    pointBackgroundColor: [],   // 동적 설정
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    lineTension: 0.2,
                    fill: false,
                    borderDash: [6, 4],
                }
            ]
        },
        options: {
            maintainAspectRatio: false,
            layout: { padding: { left: 8, right: 20, top: 20, bottom: 0 } },
            scales: {
                xAxes: [{
                    gridLines: { display: false, drawBorder: false },
                    ticks: { maxTicksLimit: 10, fontSize: 11 }
                }],
                yAxes: [{
                    ticks: {
                        maxTicksLimit: 6,
                        padding: 10,
                        fontSize: 11,
                        callback: v => fmt(v, 0) + '원'
                    },
                    gridLines: {
                        color: 'rgba(234,236,244,1)',
                        zeroLineColor: 'rgba(234,236,244,1)',
                        drawBorder: false,
                        borderDash: [2],
                    }
                }]
            },
            legend: {
                display: true,
                position: 'top',
                labels: { boxWidth: 12, fontSize: 11, padding: 16 }
            },
            tooltips: {
                backgroundColor: '#fff',
                titleFontColor: '#2c3e50',
                bodyFontColor: '#6e707e',
                borderColor: '#dddfeb',
                borderWidth: 1,
                xPadding: 14, yPadding: 12,
                displayColors: true,
                intersect: false,
                mode: 'index',
                callbacks: {
                    label: function(item, data) {
                        var lbl = data.datasets[item.datasetIndex].label;
                        if (item.yLabel == null) return null;
                        return lbl + ': ' + fmt(item.yLabel, 1) + ' 원/kg';
                    }
                }
            },
            /* 수직선 플러그인 (기준일 표시) */
            annotation: undefined
        }
    });
}


/* ============================================================
   차트 B : 방향성 확률 수평 바 차트
   ============================================================ */
function buildProbChart(ctx) {
    return new Chart(ctx, {
        type: 'horizontalBar',
        data: {
            labels: ['10일 후', '30일 후', '60일 후'],
            datasets: [{
                label: '상승 확률 (%)',
                data: [50, 50, 50],
                backgroundColor: [
                    'rgba(58, 134, 200, 0.6)',
                    'rgba(58, 134, 200, 0.6)',
                    'rgba(58, 134, 200, 0.6)'
                ],
                borderColor: [
                    'rgba(58, 134, 200, 1)',
                    'rgba(58, 134, 200, 1)',
                    'rgba(58, 134, 200, 1)'
                ],
                borderWidth: 1.5,
                borderRadius: 4,
            }]
        },
        options: {
            maintainAspectRatio: false,
            layout: { padding: { left: 0, right: 20, top: 10, bottom: 0 } },
            scales: {
                xAxes: [{
                    ticks: {
                        min: 0, max: 100,
                        stepSize: 25,
                        callback: v => v + '%',
                        fontSize: 11
                    },
                    gridLines: {
                        color: 'rgba(234,236,244,1)',
                        drawBorder: false
                    }
                }],
                yAxes: [{
                    gridLines: { display: false, drawBorder: false },
                    ticks: { fontSize: 12, fontStyle: 'bold' }
                }]
            },
            legend: { display: false },
            tooltips: {
                backgroundColor: '#fff',
                titleFontColor: '#2c3e50',
                bodyFontColor: '#6e707e',
                borderColor: '#dddfeb',
                borderWidth: 1,
                callbacks: {
                    label: function(item) {
                        var pct = item.xLabel;
                        var dir = pct >= 50 ? '▲ 상승' : '▼ 하락';
                        return '상승 확률 ' + fmt(pct, 1) + '%  →  ' + dir;
                    }
                }
            }
        }
    });
}


/* ============================================================
   방향성 차트 데이터 업데이트
   ============================================================ */
async function updateDirectionCharts(baseDate) {
    try {
        /* 1) 가격 히스토리 (최근 60일) */
        const histRes  = await fetch(API_CONFIG.FLASK_API + '/price-history?days=60');
        const histJson = histRes.ok ? await histRes.json() : { history: [] };
        const history  = histJson.history || [];

        /* 2) 이진 분류 예측 */
        const predRes  = await fetch(API_CONFIG.FLASK_API + '/get-all-binary-predictions');
        const predJson = predRes.ok ? await predRes.json() : { predictions: [] };
        const preds    = {};
        (predJson.predictions || []).forEach(p => { preds[p.horizon] = p; });

        /* ── 히스토리 라벨·데이터 ── */
        const histLabels = history.map(r => shortDate(r.date));
        const histPrices = history.map(r => r.price);

        /* ── 기준가격 (히스토리 마지막값 또는 dashboard 현재가) ── */
        const basePrice = histPrices.length > 0 ? histPrices[histPrices.length - 1] : null;

        /* ── 예측 포인트 구성 ── */
        const forecastLabels = [shortDate(baseDate)];
        const forecastData   = [basePrice];
        const dotColors      = ['rgba(58, 134, 200, 0.9)'];  // 기준점: 파란색

        [10, 30, 60].forEach(h => {
            const p = preds[h];
            forecastLabels.push(shortDate(addDays(baseDate, h)));
            if (p) {
                const isUp = p.direction === 'UP';
                /* 예측 가격 없으므로 기준가격 * (1 ± prob) 로 방향 시각화 */
                const factor = isUp ? 1 + (p.probability - 0.5) * 0.06
                                    : 1 - (0.5 - p.probability) * 0.06;
                forecastData.push(basePrice ? +(basePrice * factor).toFixed(1) : null);
                dotColors.push(isUp ? 'rgba(28, 200, 138, 1)' : 'rgba(231, 74, 59, 1)');
            } else {
                forecastData.push(null);
                dotColors.push('rgba(180,180,180,0.7)');
            }
        });

        /* ── 차트 A 업데이트 ── */
        if (directionChart) {
            const allLabels = [...histLabels, ...forecastLabels.slice(1)];
            const actualData = [...histPrices, ...Array(forecastLabels.length - 1).fill(null)];
            const forecastFull = [...Array(histPrices.length - 1).fill(null), ...forecastData];
            const dotColorsFull = [
                ...Array(histPrices.length - 1).fill('transparent'),
                ...dotColors
            ];

            directionChart.data.labels                       = allLabels;
            directionChart.data.datasets[0].data             = actualData;
            directionChart.data.datasets[1].data             = forecastFull;
            directionChart.data.datasets[1].pointBackgroundColor = dotColorsFull;
            directionChart.data.datasets[1].borderColor =
                (preds[10] && preds[10].direction === 'DOWN')
                    ? 'rgba(231, 74, 59, 0.9)'
                    : 'rgba(28, 200, 138, 0.9)';
            directionChart.update();
        }

        /* ── 차트 B 업데이트 ── */
        if (probChart) {
            const probs  = [10, 30, 60].map(h => preds[h] ? +(preds[h].probability * 100).toFixed(1) : 50);
            const colors = probs.map(p =>
                p >= 50 ? 'rgba(28, 200, 138, 0.65)' : 'rgba(231, 74, 59, 0.65)'
            );
            const borders = probs.map(p =>
                p >= 50 ? 'rgba(28, 200, 138, 1)' : 'rgba(231, 74, 59, 1)'
            );
            probChart.data.datasets[0].data            = probs;
            probChart.data.datasets[0].backgroundColor = colors;
            probChart.data.datasets[0].borderColor     = borders;
            probChart.update();
        }

        /* ── 예측 포인트 요약 텍스트 ── */
        [10, 30, 60].forEach(h => {
            const el = document.getElementById('fc-label-' + h);
            if (!el) return;
            const p = preds[h];
            if (p) {
                const isUp = p.direction === 'UP';
                const pct  = (p.probability * 100).toFixed(1);
                el.innerHTML = isUp
                    ? '<span style="color:#1cc88a;">▲ 상승</span> <span class="small text-muted">(' + pct + '%)</span>'
                    : '<span style="color:#e74a3b;">▼ 하락</span> <span class="small text-muted">(' + pct + '%)</span>';
            } else {
                el.textContent = '--';
            }
        });

    } catch(e) {
        console.warn('[방향성 차트 업데이트 실패]', e.message);
    }
}


/* ============================================================
   대시보드 KPI (단가·특별구매가·물동량) 로드
   ============================================================ */
async function loadDashboardKPI(date) {
    try {
        const res  = await fetch(API_CONFIG.FLASK_API + '/get-dashboard-data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date })
        });
        if (!res.ok) return;
        const d = await res.json();

        const priceEl   = document.querySelector('.price-prediction');
        const specEl    = document.querySelector('.special-price-prediction');
        const volEl     = document.querySelector('.volume-prediction');
        const progBar   = document.querySelector('.progress-bar');

        if (priceEl && d.price)         priceEl.textContent         = d.price;
        if (specEl  && d.special_price) specEl.textContent          = d.special_price;
        if (volEl   && d.volume) {
            const volVal = parseFloat(d.volume);
            volEl.textContent = fmt(volVal, 1) + ' ton';
            if (progBar) {
                const pct = Math.min((volVal / 5000) * 100, 100);
                progBar.style.width = pct + '%';
                progBar.setAttribute('aria-valuenow', volVal);
            }
        }
    } catch(e) {
        console.warn('[KPI 로드 실패]', e.message);
    }
}


/* ============================================================
   초기화 진입점
   ============================================================ */
document.addEventListener('DOMContentLoaded', async function() {

    /* 차트 초기화 */
    const ctxDir  = document.getElementById('dashboard_directionChart');
    const ctxProb = document.getElementById('dashboard_probChart');
    if (ctxDir)  directionChart = buildDirectionChart(ctxDir.getContext('2d'));
    if (ctxProb) probChart      = buildProbChart(ctxProb.getContext('2d'));

    /* 기준 날짜 가져오기 */
    let baseDate = null;
    try {
        const r = await fetch(API_CONFIG.FLASK_API + '/get-last-date');
        if (r.ok) {
            const j = await r.json();
            baseDate = j.last_date || null;
        }
    } catch(e) { /* ignore */ }

    /* 날짜 피커 초기화 */
    const dp = document.getElementById('dashboard_datePicker');
    if (dp) {
        if (baseDate) dp.value = baseDate;
        dp.addEventListener('change', async () => {
            const sel = dp.value;
            if (!sel) return;
            await Promise.all([
                loadDashboardKPI(sel),
                updateDirectionCharts(sel),
                loadScrabData(sel)     // news.js 에 정의됨
            ]);
        });
    }

    /* 초기 데이터 로드 */
    if (baseDate) {
        await Promise.all([
            loadDashboardKPI(baseDate),
            updateDirectionCharts(baseDate),
            loadScrabData(baseDate)
        ]);
    } else {
        /* baseDate 를 못 가져온 경우 이진 예측만 로드 */
        await updateDirectionCharts(new Date().toISOString().split('T')[0]);
    }

    /* 마지막 업데이트 라벨 */
    const lbl = document.getElementById('lastUpdateLabel');
    if (lbl && baseDate) lbl.textContent = '기준일: ' + baseDate;
});
