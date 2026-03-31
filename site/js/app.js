function demandScout() {
    return {
        activeTab: 'portfolio',
        activeSeries: 'series_b',
        loading: true,
        selectedStates: [],
        allStates: [],

        tabs: [
            { id: 'portfolio', label: 'Portfolio Overview' },
            { id: 'forecast', label: 'Demand Forecast' },
            { id: 'opportunity', label: 'Opportunity Scoring' },
            { id: 'map', label: 'Map' },
        ],

        portfolio: null,
        projections: null,
        scores: null,

        get stateEntries() {
            if (!this.portfolio?.states) return [];
            return Object.entries(this.portfolio.states)
                .sort((a, b) => b[1].centres - a[1].centres);
        },

        async init() {
            try {
                const [portfolioRes, projectionsRes, scoresRes] = await Promise.all([
                    fetch('data/arena_portfolio.json').then(r => r.json()),
                    fetch('data/abs_projections.json').then(r => r.json()),
                    fetch('data/opportunity_scores.json').then(r => r.json()),
                ]);
                this.portfolio = portfolioRes;
                this.projections = projectionsRes;
                this.scores = scoresRes;

                this.allStates = Object.keys(this.projections.states);
                this.selectedStates = [...this.allStates];

                this.loading = false;
                this.$nextTick(() => this.renderTab());
            } catch (err) {
                console.error('Failed to load data:', err);
                this.loading = false;
            }
        },

        setTab(tabId) {
            this.activeTab = tabId;
            this.$nextTick(() => this.renderTab());
        },

        setSeries(series) {
            this.activeSeries = series;
            this.$nextTick(() => this.renderTab());
        },

        toggleState(state) {
            const idx = this.selectedStates.indexOf(state);
            if (idx >= 0) {
                this.selectedStates.splice(idx, 1);
            } else {
                this.selectedStates.push(state);
            }
            this.$nextTick(() => this.renderTab());
        },

        toggleAllStates() {
            if (this.selectedStates.length === this.allStates.length) {
                this.selectedStates = [];
            } else {
                this.selectedStates = [...this.allStates];
            }
            this.$nextTick(() => this.renderTab());
        },

        scoreColor(score) {
            if (score >= 70) return 'score-high';
            if (score >= 40) return 'score-medium';
            return 'score-low';
        },

        renderTab() {
            switch (this.activeTab) {
                case 'portfolio':
                    if (this.portfolio) renderDonutChart(this.portfolio);
                    break;
                case 'forecast':
                    if (this.projections) {
                        renderForecastChart(this.projections, this.activeSeries, this.selectedStates);
                        renderForecastSummary(this.projections, this.activeSeries);
                    }
                    break;
                case 'opportunity':
                    if (this.scores) renderScatterChart(this.scores);
                    break;
                case 'map':
                    if (this.scores) initMap(this.scores);
                    break;
            }
        },
    };
}
