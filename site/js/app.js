function demandScout() {
    return {
        activeTab: 'map',
        activeSeries: 'series_b',
        loading: true,
        selectedStates: [],
        allStates: [],
        mapStateFilter: 'ALL',
        forecastMode: 'indexed',

        tabs: [
            { id: 'map', label: 'Suburb Map' },
            { id: 'forecast', label: 'Demand Forecast' },
            { id: 'portfolio', label: 'Portfolio Overview' },
            { id: 'opportunity', label: 'Opportunity Scoring' },
            { id: 'methodology', label: 'Methodology' },
        ],

        portfolio: null,
        projections: null,
        scores: null,
        sa2Boundaries: null,
        sa2Scores: null,
        stateMarket: null,

        get stateEntries() {
            if (!this.portfolio?.states) return [];
            return Object.entries(this.portfolio.states)
                .sort((a, b) => b[1].centres - a[1].centres);
        },

        get topSa2() {
            if (!this.sa2Scores?.sa2_scores) return [];
            let filtered = this.sa2Scores.sa2_scores;
            if (this.mapStateFilter && this.mapStateFilter !== 'ALL') {
                filtered = filtered.filter(s => s.state_abbr === this.mapStateFilter);
            }
            return filtered.slice(0, 20);
        },

        async init() {
            try {
                const [portfolioRes, projectionsRes, scoresRes, sa2BoundariesRes, sa2ScoresRes, stateMarketRes] = await Promise.all([
                    fetch('data/arena_portfolio.json').then(r => r.json()),
                    fetch('data/abs_projections.json').then(r => r.json()),
                    fetch('data/opportunity_scores.json').then(r => r.json()),
                    fetch('data/sa2_boundaries.geojson').then(r => r.json()),
                    fetch('data/sa2_scores.json').then(r => r.json()),
                    fetch('data/state_market.json').then(r => r.json()),
                ]);
                this.portfolio = portfolioRes;
                this.projections = projectionsRes;
                this.scores = scoresRes;
                this.sa2Boundaries = sa2BoundariesRes;
                this.sa2Scores = sa2ScoresRes;
                this.stateMarket = stateMarketRes;

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

        setMapState(state) {
            this.mapStateFilter = state;
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
                        renderForecastChart(this.projections, this.activeSeries, this.selectedStates, this.forecastMode);
                        renderShareVsGrowth(this.projections, this.activeSeries, this.stateMarket);
                        renderPortfolioBalance(this.stateMarket);
                        renderSupplyTrajectory(this.projections, this.activeSeries, this.stateMarket);
                        renderForecastHeroCards(this.projections, this.portfolio, this.activeSeries, this.stateMarket);
                        renderForecastTable(this.projections, this.portfolio, this.activeSeries, this.stateMarket);
                    }
                    break;
                case 'opportunity':
                    if (this.scores) renderScatterChart(this.scores);
                    break;
                case 'map':
                    if (this.sa2Boundaries && this.sa2Scores) {
                        initSa2Map(this.sa2Boundaries, this.sa2Scores, this.mapStateFilter);
                    }
                    break;
            }
        },
    };
}
