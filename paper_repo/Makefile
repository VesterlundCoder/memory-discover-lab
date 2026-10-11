PYTHON ?= python

.PHONY: pdf figures verify reproduce
pdf:
	mkdir -p build
	pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build paper.tex
	pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build paper.tex
	pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build supplement/supplement.tex
	pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build supplement/supplement.tex
	cp build/paper.pdf paper.pdf
	cp build/supplement.pdf supplement/supplement.pdf

figures:
	$(PYTHON) scripts/make_figures.py
	$(PYTHON) scripts/make_tables.py

verify:
	$(PYTHON) scripts/verify_results.py

reproduce:
	$(PYTHON) scripts/reproduce.py
