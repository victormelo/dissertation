all:
	latexmk -gg -bibtex-cond -pdf -pvc dissertation_vkslm.tex
clean:
	@rm -f *.out *.aux *.alg *.brf *.acr *.dvi *.gls *.log *.bbl *.blg *.ntn *.not *.lof *.lot *.toc *.loa *.lsg *.nlo *.nls *.ilg *.ind *.ist *.glg *.glo *.xdy *.acn *.idx *.loq *.synctex.gz *~

