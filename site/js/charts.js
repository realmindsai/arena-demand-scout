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


function renderForecastChart(projections, activeSeries, selectedStates, mode) {
    const years = projections.projection_years;
    const baseIdx = years.indexOf(2026);
    const indexed = mode === 'indexed';
    const traces = [];

    for (const state of selectedStates) {
        const stateData = projections.states[state];
        if (!stateData || !stateData[activeSeries]) continue;

        const pop = stateData[activeSeries].population_0_5;
        const baseVal = baseIdx >= 0 ? pop[baseIdx] : pop[0];
        const color = STATE_COLORS[state] || '#94a3b8';

        const yValues = indexed
            ? pop.map(v => ((v - baseVal) / baseVal * 100))
            : pop;

        traces.push({
            x: years.slice(0, pop.length),
            y: yValues,
            name: state,
            type: 'scatter',
            mode: 'lines+markers',
            line: { color, width: 3 },
            marker: { size: 4 },
            hovertemplate: indexed
                ? `${state}: %{y:+.1f}%<extra>%{x}</extra>`
                : `${state}: %{y:,.0f}<extra>%{x}</extra>`,
        });

        // Confidence band for medium series
        if (activeSeries === 'series_b' && stateData.series_a && stateData.series_c) {
            const high = stateData.series_a.population_0_5;
            const low = stateData.series_c.population_0_5;
            const len = Math.min(high.length, low.length);
            const bandYears = years.slice(0, len);

            const highY = indexed ? high.slice(0, len).map(v => ((v - baseVal) / baseVal * 100)) : high.slice(0, len);
            const lowY = indexed ? low.slice(0, len).map(v => ((v - baseVal) / baseVal * 100)) : low.slice(0, len);

            traces.push({
                x: [...bandYears, ...bandYears.slice().reverse()],
                y: [...highY, ...lowY.reverse()],
                fill: 'toself',
                fillcolor: color + '18',
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
        title: { text: indexed ? 'Demand Growth: Indexed from 2026' : 'Children 0\u20135 Population', font: { size: 15 } },
        xaxis: { title: '', dtick: 2, gridcolor: '#e2e8f0' },
        yaxis: {
            title: indexed ? 'Change from 2026 (%)' : 'Population (0\u20135)',
            tickformat: indexed ? '+.1f' : ',.0f',
            ticksuffix: indexed ? '%' : '',
            zeroline: indexed,
            zerolinecolor: '#94a3b8',
            gridcolor: '#e2e8f0',
        },
        legend: { orientation: 'h', y: -0.15 },
        shapes: [{
            type: 'line', x0: todayYear, x1: todayYear,
            y0: 0, y1: 1, yref: 'paper',
            line: { color: '#94a3b8', width: 1, dash: 'dash' },
        }],
        annotations: indexed ? [{
            x: todayYear, y: 1, yref: 'paper', xanchor: 'left',
            text: ' Today', showarrow: false,
            font: { size: 11, color: '#94a3b8' },
        }] : [],
    };

    Plotly.newPlot('chart-forecast', traces, layout, PLOTLY_CONFIG);
}


function renderDemandPerCentre(projections, portfolio, activeSeries, stateMarket) {
    const el = document.getElementById('chart-demand-per-centre');
    if (!el || !stateMarket?.states) return;

    const states = Object.keys(stateMarket.states).filter(s =>
        stateMarket.states[s].total_centres > 0 && (portfolio?.states?.[s]?.centres || 0) > 0
    );
    states.sort((a, b) => stateMarket.states[b].children_per_centre - stateMarket.states[a].children_per_centre);

    const marketKpc = [];
    const arenaKpc = [];
    for (const s of states) {
        const m = stateMarket.states[s];
        const arenaCentres = portfolio.states[s]?.centres || 0;
        marketKpc.push(m.children_per_centre);
        arenaKpc.push(arenaCentres > 0 ? Math.round(m.pop_0_4 / arenaCentres) : 0);
    }

    const data = [
        {
            x: states, y: marketKpc, name: 'All Providers',
            type: 'bar', marker: { color: '#94a3b8' },
            hovertemplate: '%{x}: %{y:,.0f} kids/centre<extra>All Providers</extra>',
        },
        {
            x: states, y: arenaKpc, name: 'Arena REIT',
            type: 'bar', marker: { color: '#059669' },
            hovertemplate: '%{x}: %{y:,.0f} kids/centre<extra>Arena REIT</extra>',
        },
    ];

    const layout = {
        ...PLOTLY_LAYOUT_BASE,
        title: { text: 'Children per Centre: Market vs Arena', font: { size: 14 } },
        barmode: 'group',
        xaxis: { title: '' },
        yaxis: { title: '', tickformat: ',.0f' },
        legend: { orientation: 'h', y: -0.12 },
        margin: { t: 40, r: 10, b: 40, l: 55 },
    };

    Plotly.newPlot(el, data, layout, PLOTLY_CONFIG);
}


function renderForecastHeroCards(projections, portfolio, activeSeries, stateMarket) {
    const el = document.getElementById('forecast-hero-cards');
    if (!el || !portfolio?.states) return;

    const years = projections.projection_years;
    const idx2026 = years.indexOf(2026);
    const idx2031 = years.indexOf(2031);

    // National totals
    let natPop26 = 0, natPop31 = 0;
    for (const [state, data] of Object.entries(projections.states)) {
        const pop = data[activeSeries]?.population_0_5;
        if (pop) {
            natPop26 += pop[idx2026] || 0;
            natPop31 += pop[idx2031] || 0;
        }
    }
    const natGrowth = ((natPop31 - natPop26) / natPop26 * 100).toFixed(1);
    const additionalKids = natPop31 - natPop26;

    // Fastest growing state
    let maxGrowth = -Infinity, fastestState = '';
    for (const [state, data] of Object.entries(projections.states)) {
        const pop = data[activeSeries]?.population_0_5;
        if (pop && pop[idx2026] > 0) {
            const g = (pop[idx2031] - pop[idx2026]) / pop[idx2026] * 100;
            if (g > maxGrowth) { maxGrowth = g; fastestState = state; }
        }
    }

    // National market share
    let totalCentres = 0, arenaCentres = 0, totalUnderserved = 0;
    if (stateMarket?.states) {
        for (const m of Object.values(stateMarket.states)) {
            totalCentres += m.total_centres;
            arenaCentres += m.arena_centres;
            totalUnderserved += m.underserved_sa2;
        }
    }
    const nationalShare = totalCentres > 0 ? (arenaCentres / totalCentres * 100).toFixed(1) : '0';

    el.innerHTML = `
        <div class="bg-white rounded-lg shadow p-5">
            <p class="text-sm text-slate-500 mb-1">National Growth (2026\u20132031)</p>
            <p class="text-3xl font-bold ${parseFloat(natGrowth) > 0 ? 'text-emerald-600' : 'text-red-600'}">+${natGrowth}%</p>
            <p class="text-xs text-slate-400 mt-1">+${additionalKids.toLocaleString()} children 0\u20135</p>
        </div>
        <div class="bg-white rounded-lg shadow p-5">
            <p class="text-sm text-slate-500 mb-1">Fastest Growing State</p>
            <p class="text-3xl font-bold text-emerald-600">${fastestState}</p>
            <p class="text-xs text-slate-400 mt-1">+${maxGrowth.toFixed(1)}% projected by 2031</p>
        </div>
        <div class="bg-white rounded-lg shadow p-5">
            <p class="text-sm text-slate-500 mb-1">Arena National Market Share</p>
            <p class="text-3xl font-bold text-teal-600">${nationalShare}%</p>
            <p class="text-xs text-slate-400 mt-1">${arenaCentres} of ${totalCentres.toLocaleString()} centres</p>
        </div>
        <div class="bg-white rounded-lg shadow p-5">
            <p class="text-sm text-slate-500 mb-1">Underserved SA2 Regions</p>
            <p class="text-3xl font-bold text-amber-600">${totalUnderserved}</p>
            <p class="text-xs text-slate-400 mt-1">scoring \u226560 (demand exceeds supply)</p>
        </div>
    `;
}


function renderForecastTable(projections, portfolio, activeSeries, stateMarket) {
    const el = document.getElementById('forecast-table-body');
    if (!el || !stateMarket?.states) return;

    const years = projections.projection_years;
    const idx2026 = years.indexOf(2026);
    const idx2031 = years.indexOf(2031);

    const rows = [];
    for (const [state, m] of Object.entries(stateMarket.states)) {
        const pop = projections.states[state]?.[activeSeries]?.population_0_5;
        const pop26 = pop ? (pop[idx2026] || 0) : m.pop_0_4;
        const pop31 = pop ? (pop[idx2031] || pop26) : pop26;
        const growth = pop26 > 0 ? ((pop31 - pop26) / pop26 * 100) : 0;

        rows.push({
            state,
            pop: m.pop_0_4,
            growth,
            totalCentres: m.total_centres,
            kpc: m.children_per_centre,
            arenaCentres: m.arena_centres,
            arenaShare: m.arena_market_share_pct,
            underserved: m.underserved_sa2,
            totalSa2: m.total_sa2,
        });
    }

    rows.sort((a, b) => b.underserved - a.underserved);

    el.innerHTML = rows.map(r => {
        const underservedPct = r.totalSa2 > 0 ? (r.underserved / r.totalSa2 * 100).toFixed(0) : 0;
        return `
        <tr class="border-t border-slate-100 hover:bg-slate-50">
            <td class="px-4 py-2 font-medium">${r.state}</td>
            <td class="px-4 py-2 text-right tabular-nums">${r.pop.toLocaleString()}</td>
            <td class="px-4 py-2 text-right">
                <span class="font-semibold ${r.growth > 0 ? 'text-emerald-600' : 'text-red-600'}">${r.growth > 0 ? '+' : ''}${r.growth.toFixed(1)}%</span>
            </td>
            <td class="px-4 py-2 text-right tabular-nums">${r.totalCentres.toLocaleString()}</td>
            <td class="px-4 py-2 text-right tabular-nums ${r.kpc > 90 ? 'text-amber-600 font-semibold' : ''}">${r.kpc.toFixed(0)}</td>
            <td class="px-4 py-2 text-right tabular-nums">${r.arenaCentres}</td>
            <td class="px-4 py-2 text-right tabular-nums">${r.arenaShare.toFixed(1)}%</td>
            <td class="px-4 py-2 text-right">
                <span class="font-semibold ${r.underserved > 50 ? 'text-amber-600' : 'text-slate-600'}">${r.underserved}</span>
                <span class="text-slate-400 text-xs"> / ${r.totalSa2} (${underservedPct}%)</span>
            </td>
        </tr>
    `}).join('');
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
