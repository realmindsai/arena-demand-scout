.PHONY: build test serve clean

build:
	uv run python build.py

test:
	uv run pytest tests/ -v --ignore=tests/test_e2e.py

test-e2e:
	uv run pytest tests/test_e2e.py -v

serve:
	cd site && python -m http.server 8000

clean:
	rm -rf site/data/*.json .abs_cache/
