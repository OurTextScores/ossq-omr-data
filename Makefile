.DEFAULT_GOAL := help

check-inputs:

	python3 scripts/check_inputs.py --ossq "$(OSSQ_SOURCE)" --preprocessor "$(PREPROCESSOR_SOURCE)"

preprocess: check-inputs

	@echo "Run the numbered OSSQ source pipeline in $(PREPROCESSOR_SOURCE) against $(OSSQ_SOURCE)."
	@echo "This target does not download scans without the operator reviewing their source terms."

package: check-inputs

	test -n "$(OUT)"
	python3 tools/package_dataset.py --root "$(OUT)"

verify:

	test -n "$(OUT)"
	python3 tools/package_dataset.py --root "$(OUT)" --verify-only

help:

	@echo "Set OSSQ_SOURCE, PREPROCESSOR_SOURCE, and OUT; then run make check-inputs."
