let mapInstance = null;

function initMap(scores) {
    const container = document.getElementById('map-container');
    if (!container) return;

    if (mapInstance) {
        mapInstance.remove();
        mapInstance = null;
    }

    mapInstance = L.map(container).setView([-28, 134], 4);

    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://carto.com/">CARTO</a>',
        maxZoom: 10,
    }).addTo(mapInstance);

    const scoreLookup = {};
    for (const r of (scores.rankings || [])) {
        scoreLookup[r.state] = r;
    }

    fetch('assets/geo/aus_states.geojson')
        .then(r => r.json())
        .then(geojson => {
            L.geoJSON(geojson, {
                style: feature => {
                    const stateName = feature.properties.STATE_NAME
                        || feature.properties.name
                        || feature.properties.STE_NAME21
                        || '';
                    const abbr = stateAbbr(stateName);
                    const entry = scoreLookup[abbr];
                    return {
                        fillColor: entry ? scoreToColor(entry.opportunity_score) : '#e2e8f0',
                        weight: 1,
                        opacity: 1,
                        color: '#94a3b8',
                        fillOpacity: 0.7,
                    };
                },
                onEachFeature: (feature, layer) => {
                    const stateName = feature.properties.STATE_NAME
                        || feature.properties.name
                        || feature.properties.STE_NAME21
                        || 'Unknown';
                    const abbr = stateAbbr(stateName);
                    const entry = scoreLookup[abbr];

                    if (entry) {
                        layer.bindPopup(`
                            <div class="text-sm">
                                <p class="font-bold">${stateName} (${abbr})</p>
                                <p>Centres: ${entry.centre_count}</p>
                                <p>Demand Growth: ${entry.demand_growth_pct}%</p>
                                <p>Supply Density: ${entry.current_supply_density}</p>
                                <p>Score: <strong>${entry.opportunity_score}</strong> (${entry.verdict})</p>
                            </div>
                        `);
                    }

                    layer.on('mouseover', () => layer.setStyle({ fillOpacity: 0.9, weight: 2 }));
                    layer.on('mouseout', () => layer.setStyle({ fillOpacity: 0.7, weight: 1 }));
                },
            }).addTo(mapInstance);
        })
        .catch(err => console.error('Failed to load GeoJSON:', err));
}


function scoreToColor(score) {
    if (score >= 70) return '#059669';
    if (score >= 40) return '#d97706';
    return '#dc2626';
}


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
