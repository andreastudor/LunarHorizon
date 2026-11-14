"""Astronomie prin SPICE: kerneluri, timp, direcțiile Soarelui și Pământului.

Convențiile sunt în docs/SPEC_FIZICA.md §2, §3.1 și §5.

Kernelurile se descarcă și se verifică cu scripts/download_kernels.py. Apelurile SpiceyPy trec prin
`SPICE_LOCK`, fiindcă biblioteca SPICE nu este sigură pentru fire de execuție.
"""
