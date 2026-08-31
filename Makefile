.DEFAULT_GOAL := help

check-inputs:

	python3 scripts/check_inputs.py --ossq "$(OSSQ_SOURCE)" --preprocessor "$(PREPROCESSOR_SOURCE)" --homr "$(HOMR_SOURCE)"

preprocess: check-inputs

	@echo "Run the numbered OSSQ source pipeline in $(PREPROCESSOR_SOURCE) against $(OSSQ_SOURCE)."
	@echo "This target does not download scans without the operator reviewing their source terms."

package: check-inputs

	test -n "$(OUT)"
	cd "$(HOMR_SOURCE)" && python3 -m training.omr_datasets.package_dataset --root "$(OUT)"

verify:

	test -n "$(OUT)"
	cd "$(HOMR_SOURCE)" && python3 -m training.omr_datasets.package_dataset --root "$(OUT)" --verify-only

help:

	@echo "Set OSSQ_SOURCE, PREPROCESSOR_SOURCE, HOMR_SOURCE, and OUT; then run make check-inputs."
