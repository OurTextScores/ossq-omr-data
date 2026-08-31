.DEFAULT_GOAL := help

SOURCE_DIR ?= sources
ARCHIVE_BASE_URL ?=

fetch-source:
	python3 scripts/fetch_source.py ossq --dest "$(SOURCE_DIR)" $(if $(ARCHIVE_BASE_URL),--base-url "$(ARCHIVE_BASE_URL)")

extract-source: fetch-source
	python3 scripts/fetch_source.py ossq --dest "$(SOURCE_DIR)" --extract

check-inputs: extract-source
	python3 scripts/check_inputs.py --ossq "$(SOURCE_DIR)/ossq-source"

package:
	test -n "$(OUT)"
	python3 tools/package_dataset.py --root "$(OUT)"

verify:
	test -n "$(OUT)"
	python3 tools/package_dataset.py --root "$(OUT)" --verify-only

help:
	@echo "make extract-source     Fetch, SHA-256 verify, and extract the locked OSSQ source snapshot."
	@echo "make package OUT=/path  Verify a materialized portable dataset."
