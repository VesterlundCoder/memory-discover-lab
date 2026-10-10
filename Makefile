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

.PHONY: eval-step1 eval-step3 eval-step4 test-evaluation
eval-step1:
	$(PYTHON) scripts/evaluate_system.py step1 --out evaluation/results/local-step1
eval-step3:
	$(PYTHON) scripts/evaluate_system.py step3 --out evaluation/results/local-step3
eval-step4:
	$(PYTHON) scripts/evaluate_system.py step4 --out evaluation/results/local-step4
test-evaluation:
	$(PYTHON) -m unittest discover -s evaluation/tests -v
