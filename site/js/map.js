let mapInstance = null;
let sa2Layer = null;
let stateLayer = null;

function initSa2Map(geojsonData, sa2Scores, stateFilter) {
    const container = document.getElementById('map-container');
    if (!container) return;

    // Build score lookup from sa2_scores
    const scoreLookup = {};
    for (const entry of (sa2Scores?.sa2_scores || [])) {
        scoreLookup[entry.sa2_code] = entry;
    }

    if (!mapInstance) {
        mapInstance = L.map(container).setView([-28, 134], 5);
        L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://carto.com/">CARTO</a>',
            maxZoom: 16,
        }).addTo(mapInstance);
    }

    // Remove existing SA2 layer
    if (sa2Layer) {
        mapInstance.removeLayer(sa2Layer);
        sa2Layer = null;
    }

    // Filter features by state
    const filteredFeatures = geojsonData.features.filter(f => {
        if (!stateFilter || stateFilter === 'ALL') return true;
        const stateCode = String(f.properties.state_code_2021 || '');
        return STATE_CODE_MAP[stateFilter] === stateCode;
    });

    const filteredGeoJson = {
        type: 'FeatureCollection',
        features: filteredFeatures,
    };

    sa2Layer = L.geoJSON(filteredGeoJson, {
        style: feature => {
            const code = String(feature.properties.sa2_code_2021 || '');
            const entry = scoreLookup[code];
            const score = entry ? entry.demand_score : 0;
            return {
                fillColor: demandScoreColor(score),
                weight: 0.5,
                opacity: 0.6,
                color: '#64748b',
                fillOpacity: 0.7,
            };
        },
        onEachFeature: (feature, layer) => {
            const props = feature.properties;
            const code = String(props.sa2_code_2021 || '');
            const entry = scoreLookup[code] || {};
            const pop = entry.pop_0_4 || props.pop_0_4 || 0;
            const density = entry.children_per_sqkm || props.children_per_sqkm || 0;
            const score = entry.demand_score || 0;
            const verdict = entry.verdict || 'N/A';
            const area = props.area_albers_sqkm ? props.area_albers_sqkm.toFixed(1) : 'N/A';

            const centres = entry.centre_count || props.centre_count || 0;
            const places = entry.approved_places || props.approved_places || 0;
            const ppc = entry.places_per_child || props.places_per_child || 0;

            layer.bindPopup(`
                <div class="text-sm" style="min-width: 220px">
                    <p class="font-bold text-base">${props.sa2_name_2021 || 'Unknown'}</p>
                    <p class="text-gray-500">${props.state_abbr || ''}</p>
                    <hr class="my-1">
                    <p><strong>Demand</strong></p>
                    <p>Children 0-4: <strong>${pop.toLocaleString()}</strong></p>
                    <p>Density: ${density.toFixed(1)} per km²</p>
                    <hr class="my-1">
                    <p><strong>Supply</strong></p>
                    <p>Childcare centres: <strong>${centres}</strong></p>
                    <p>Approved places: <strong>${places.toLocaleString()}</strong></p>
                    <p>Places per child: <strong>${ppc.toFixed(2)}</strong></p>
                    <hr class="my-1">
                    <p>Opportunity Score: <strong style="color: ${demandScoreColor(score)}">${score}</strong> — ${verdict}</p>
                </div>
            `);

            layer.on('mouseover', () => {
                layer.setStyle({ fillOpacity: 0.95, weight: 2, color: '#1e293b' });
                layer.bringToFront();
            });
            layer.on('mouseout', () => {
                layer.setStyle({ fillOpacity: 0.7, weight: 0.5, color: '#64748b' });
            });
        },
    }).addTo(mapInstance);

    // Auto-zoom to filtered region
    if (filteredFeatures.length > 0) {
        const bounds = sa2Layer.getBounds();
        if (bounds.isValid()) {
            mapInstance.fitBounds(bounds, { padding: [20, 20] });
        }
    }
}


function demandScoreColor(score) {
    // Continuous green gradient: darker green = higher demand
    if (score >= 80) return '#065f46';  // emerald-800
    if (score >= 70) return '#047857';  // emerald-700
    if (score >= 60) return '#059669';  // emerald-600
    if (score >= 50) return '#10b981';  // emerald-500
    if (score >= 40) return '#34d399';  // emerald-400
    if (score >= 30) return '#6ee7b7';  // emerald-300
    if (score >= 20) return '#a7f3d0';  // emerald-200
    if (score >= 10) return '#d1fae5';  // emerald-100
    return '#f0fdf4';                   // emerald-50
}


// State abbreviation → ABS state code
const STATE_CODE_MAP = {
    NSW: '1', VIC: '2', QLD: '3', SA: '4',
    WA: '5', TAS: '6', NT: '7', ACT: '8',
};


// Legacy state-level map (kept for Tab 4 compatibility if needed)
const STATE_ABBR_MAP = {
    'new south wales': 'NSW',
    'victoria': 'VIC',
    'queensland': 'QLD',
    'south australia': 'SA',
    'western australia': 'WA',
    'tasmania': 'TAS',
    'northern territory': 'NT',
    'australian capital territory': 'ACT',
};

function stateAbbr(name) {
    if (name.length <= 3) return name.toUpperCase();
    return STATE_ABBR_MAP[name.toLowerCase()] || name;
}
