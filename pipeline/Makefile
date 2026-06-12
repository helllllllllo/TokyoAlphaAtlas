.PHONY: refresh test dev-data
refresh:
	uv run python -m atlas.cli refresh
test:
	uv run pytest -q
dev-data:
	mkdir -p /tmp/atlas-devraw/hazard
	cp tests/fixtures/a31_flood.geojson /tmp/atlas-devraw/hazard/flood.geojson
	cp tests/fixtures/a33_landslide.geojson /tmp/atlas-devraw/hazard/landslide.geojson
	uv run python -m atlas.cli refresh \
	  --tx-dir tests/fixtures/transactions \
	  --n02 tests/fixtures/n02_stations.geojson \
	  --s12 tests/fixtures/s12_ridership.geojson \
	  --hazard-dir /tmp/atlas-devraw/hazard \
	  --population tests/fixtures/pop_mesh.geojson \
	  --landprice-dir tests/fixtures/landprice \
	  --out-dir ../web/public/data \
	  --db-path /tmp/atlas-dev.duckdb
