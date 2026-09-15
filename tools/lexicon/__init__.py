"""
Pipeline du lexique de Terminator.

Construit, à partir du DELA, de Lexique 3.83 et du Wiktionnaire, une base locale qui aide
l'auteur à trier les mots, puis exporte le lexique curé selon ses décisions
(`data/lexicon/decisions.csv`). Voir docs/LEXICON.md.

Usage : python -m tools.lexicon {download,build,export,stats}
"""
