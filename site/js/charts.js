const STATE_COLORS = {
    NSW: '#2563eb', VIC: '#059669', QLD: '#d97706',
    SA: '#dc2626', WA: '#7c3aed', TAS: '#0891b2',
    NT: '#be185d', ACT: '#65a30d',
};

const PLOTLY_LAYOUT_BASE = {
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { family: 'system-ui, sans-serif', color: '#334155' },
    margin: { t: 40, r: 20, b: 40, l: 60 },
};

const PLOTLY_CONFIG = { responsive: true, displayModeBar: false };


function renderDonutChart(portfolio) {
    const states = Object.keys(portfolio.states);
    const centres = states.map(s => portfolio.states[s].centres);

    const data = [{
        type: 'pie',
        hole: 0.5,
        labels: states,
        values: centres,
        marker: { colors: states.map(s => STATE_COLORS[s] || '#94a3b8') },
        textinfo: 'label+percent',
        textposition: 'outside',
        hovertemplate: '%{label}: %{value} centres<extra></extra>',
    }];

    const layout = {
        ...PLOTLY_LAYOUT_BASE,
        title: { text: 'Centre Distribution by State', font: { size: 16 } },
        showlegend: false,
    };

    Plotly.newPlot('chart-donut', data, layout, PLOTLY_CONFIG);
}


function renderForecastChart(projections, activeSeries, selectedStates) {
    const years = projections.projection_years;
    const traces = [];

    for (const state of selectedStates) {
        const stateData = projections.states[state];
        if (!stateData || !stateData[activeSeries]) continue;

        const pop = stateData[activeSeries].population_0_5;
        const color = STATE_COLORS[state] || '#94a3b8';

        traces.push({
            x: years.slice(0, pop.length),
            y: pop,
            name: state,
            type: 'scatter',
            mode: 'lines',
            line: { color, width: 2 },
            hovertemplate: `${state}: %{y:,.0f}<extra>%{x}</extra>`,
        });

        if (activeSeries === 'series_b' && stateData.series_a && stateData.series_c) {
            const high = stateData.series_a.population_0_5;
            const low = stateData.series_c.population_0_5;
            const bandYears = years.slice(0, Math.min(high.length, low.length));

            traces.push({
                x: [...bandYears, ...bandYears.slice().reverse()],
                y: [...high.slice(0, bandYears.length), ...low.slice(0, bandYears.length).reverse()],
                fill: 'toself',
                fillcolor: color + '15',
                line: { color: 'transparent' },
                showlegend: false,
                hoverinfo: 'skip',
                type: 'scatter',
            });
        }
    }

    const todayYear = new Date().getFullYear();

    const layout = {
        ...PLOTLY_LAYOUT_BASE,
        title: { text: 'Children Aged 0-5: Population Projections', font: { size: 16 } },
        xaxis: { title: 'Year', dtick: 2 },
        yaxis: { title: 'Population (0-5)', tickformat: ',.0f' },
        legend: { orientation: 'h', y: -0.15 },
        shapes: [{
            type: 'line', x0: todayYear, x1: todayYear,
            y0: 0, y1: 1, yref: 'paper',
            line: { color: '#94a3b8', width: 1, dash: 'dash' },
        }],
    };

    Plotly.newPlot('chart-forecast', traces, layout, PLOTLY_CONFIG);
}


function renderForecastSummary(projections, activeSeries) {
    const grid = document.getElementById('forecast-summary-grid');
    if (!grid) return;
    grid.innerHTML = '';

    const years = projections.projection_years;
    const idx2026 = years.indexOf(2026);
    const idx2031 = years.indexOf(2031);
    const idx2036 = years.indexOf(2036);

    for (const [state, data] of Object.entries(projections.states)) {
        const pop = data[activeSeries]?.population_0_5;
        if (!pop || idx2026 < 0) continue;

        const growth2031 = idx2031 >= 0
            ? ((pop[idx2031] - pop[idx2026]) / pop[idx2026] * 100).toFixed(1)
            : 'N/A';
        const growth2036 = idx2036 >= 0
            ? ((pop[idx2036] - pop[idx2026]) / pop[idx2026] * 100).toFixed(1)
            : 'N/A';

        const div = document.createElement('div');
        div.className = 'p-3 rounded bg-slate-50';
        div.innerHTML = `
            <p class="font-semibold text-slate-700">${state}</p>
            <p class="text-xs text-slate-500">2031: <span class="font-medium ${parseFloat(growth2031) > 0 ? 'text-green-600' : 'text-red-600'}">${growth2031 > 0 ? '+' : ''}${growth2031}%</span></p>
            <p class="text-xs text-slate-500">2036: <span class="font-medium ${parseFloat(growth2036) > 0 ? 'text-green-600' : 'text-red-600'}">${growth2036 > 0 ? '+' : ''}${growth2036}%</span></p>
        `;
        grid.appendChild(div);
    }
}


function renderScatterChart(scores) {
    const rankings = scores.rankings || [];

    const data = [{
        x: rankings.map(r => r.current_supply_density),
        y: rankings.map(r => r.demand_growth_pct),
        text: rankings.map(r => r.state),
        customdata: rankings.map(r => r.centre_count),
        mode: 'markers+text',
        type: 'scatter',
        textposition: 'top center',
        marker: {
            size: rankings.map(r => Math.max(10, r.centre_count / 3)),
            color: rankings.map(r => {
                if (r.opportunity_score >= 70) return '#059669';
                if (r.opportunity_score >= 40) return '#d97706';
                return '#dc2626';
            }),
            opacity: 0.8,
            line: { color: '#fff', width: 1 },
        },
        hovertemplate: '%{text}<br>Supply Density: %{x}<br>Demand Growth: %{y}%<br>Centres: %{customdata}<extra></extra>',
    }];

    const layout = {
        ...PLOTLY_LAYOUT_BASE,
        title: { text: 'Opportunity Matrix', font: { size: 16 } },
        xaxis: { title: 'Supply Density (centres per 1,000 children 0-5)' },
        yaxis: { title: 'Demand Growth % (2026-2031)' },
        shapes: rankings.length > 0 ? [{
            type: 'line',
            x0: median(rankings.map(r => r.current_supply_density)),
            x1: median(rankings.map(r => r.current_supply_density)),
            y0: 0, y1: 1, yref: 'paper',
            line: { color: '#cbd5e1', width: 1, dash: 'dot' },
        }, {
            type: 'line',
            y0: median(rankings.map(r => r.demand_growth_pct)),
            y1: median(rankings.map(r => r.demand_growth_pct)),
            x0: 0, x1: 1, xref: 'paper',
            line: { color: '#cbd5e1', width: 1, dash: 'dot' },
        }] : [],
    };

    Plotly.newPlot('chart-scatter', data, layout, PLOTLY_CONFIG);
}


function median(arr) {
    const sorted = [...arr].sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);
    return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}
