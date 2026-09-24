.DEFAULT_GOAL := help

SOURCE_DIR ?= sources
CORPUS_DIR ?= corpus
ARCHIVE_BASE_URL ?=

fetch-source:
	python3 scripts/fetch_source.py ossq --dest "$(SOURCE_DIR)" $(if $(ARCHIVE_BASE_URL),--base-url "$(ARCHIVE_BASE_URL)")

extract-source: fetch-source
	python3 scripts/fetch_source.py ossq --dest "$(SOURCE_DIR)" --extract

check-inputs: extract-source
	python3 scripts/check_inputs.py --ossq "$(SOURCE_DIR)/ossq-source"

build-stage2: check-inputs
	test -n "$(OUT)"
	python3 tools/build_ossq_stage2.py --source "$(SOURCE_DIR)/ossq-source" --out "$(OUT)" $(if $(SCORE_LIST),--score-list "$(SCORE_LIST)") $(if $(DEVICE),--device "$(DEVICE)")

fetch-corpus:
	python3 scripts/fetch_corpus.py --dest "$(CORPUS_DIR)" $(if $(SPLIT),--split "$(SPLIT)")

verify-corpus:
	python3 scripts/fetch_corpus.py --dest "$(CORPUS_DIR)" --verify-only $(if $(SPLIT),--split "$(SPLIT)")

package:
	test -n "$(OUT)"
	python3 tools/package_dataset.py --root "$(OUT)"

verify:
	test -n "$(OUT)"
	python3 tools/package_dataset.py --root "$(OUT)" --verify-only

check-stems:
	python3 tools/check_stems.py

check-rasterization:
	python3 tools/check_rasterization.py

help:
	@echo "make fetch-corpus [SPLIT=valid]      Download the built corpus (790MB, or 76MB for valid)."
	@echo "make verify-corpus [SPLIT=valid]     Re-check downloaded shards against the pinned digests."
	@echo "make extract-source     Fetch, SHA-256 verify, and extract the locked OSSQ source snapshot."
	@echo "make build-stage2 OUT=/path [SCORE_LIST=file DEVICE=cuda:0]  Build crop/token datasets."
	@echo "make package OUT=/path  Verify a materialized portable dataset."
