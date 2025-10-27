# DANS backend/test_harness.py

import time
import statistics
import signal
import contextlib
import sys
import os
from datetime import datetime
import logging
import grid_generator

print(f"[DEBUG] Fichier grid_generator importé depuis : {grid_generator.__file__}")

# On importe le chef d'orchestre et le Trie (pour charger les mots)
from grid_generator import GridGenerator
from trie_engine import DictionnaireTrie 

# --- CONFIGURATION ---
TEST_CONFIGS = [
    {'width': 6, 'height': 7, 'count': 4},  # Template plus petit pour tests rapides
]
SINGLE_GRID_TIMEOUT_SECONDS = 40  # Réduit pour les petites grilles 
DELA_FILE = 'dela_clean.csv'

class TimeoutException(Exception): pass

@contextlib.contextmanager
def time_limit(seconds):
    def signal_handler(signum, frame):
        raise TimeoutException(f"Timeout ({seconds}s)!")
    if sys.platform != "win32":
        signal.signal(signal.SIGALRM, signal_handler)
        signal.alarm(seconds)
    try:
        yield
    finally:
        if sys.platform != "win32":
            signal.alarm(0)

def load_all_words():
    """Charge tous les mots du dictionnaire et retourne une liste de STRINGS."""
    print(f"Chargement du dictionnaire complet depuis {DELA_FILE}...")
    try:
        trie = DictionnaireTrie()
        trie.load_dela_csv(DELA_FILE)
        
        # On s'assure de ne renvoyer qu'une liste de chaînes de caractères
        all_words_strings = trie.get_all_words()
        
        print(f"Dictionnaire chargé avec {len(all_words_strings)} mots uniques.")
        return all_words_strings
    except FileNotFoundError:
        print(f"ERREUR: Le fichier '{DELA_FILE}' n'a pas été trouvé.")
        return []

def run_test_batch(words, config):
    """Génère un lot de grilles et collecte les données complètes."""
    results = { "config": config, "generated_grids": [], "failures": 0, "timeouts": 0 }
    width, height, count = config['width'], config['height'], config['count']
    print(f"\n--- Lancement du batch : {count} grilles de {width}x{height} ---")

    # --- BLOC D'OPTIMISATION (AJOUTÉ) ---
    # On pré-filtre les mots et construit le Trie UNE SEULE FOIS pour ce batch.
    
    logging.info(f"Pré-filtrage des mots pour la taille {width}x{height}...")
    max_len = max(width, height)
    
    # 1. Pré-filtrer les mots (pertinents pour cette taille de grille)
    valid_words_for_batch = [w for w in words if len(w) <= max_len]

    logging.info(f"Construction du Trie partagé avec {len(valid_words_for_batch)} mots (1x)...")
    
    # 2. Construire le Trie (l'opération lente)
    shared_trie = DictionnaireTrie()
    for word in valid_words_for_batch:
        shared_trie.insert(word)
        
    logging.info("Trie partagé construit. Démarrage des générations...")
    # --- FIN DU BLOC D'OPTIMISATION ---

    for i in range(count):
        print(f"  Génération de la grille {i + 1}/{count} (seed={i})...", end='', flush=True)
        start_time = time.time()
        
        try:
            with time_limit(SINGLE_GRID_TIMEOUT_SECONDS):
                
                # --- APPEL MODIFIÉ (MAINTENANT TRÈS RAPIDE) ---
                # On passe la liste de mots DÉJÀ filtrés et le Trie DÉJÀ construit
                generator = GridGenerator(width, height, 
                                          valid_words_for_batch,   # Mots pré-filtrés
                                          prebuilt_trie=shared_trie, # Trie pré-construit
                                          seed=i)
                success = generator.generate()
            end_time = time.time()

            if success:
                grid_data = generator.get_grid_data()
                if grid_data and grid_data['fill_ratio'] > 0:
                    grid_data['generation_time'] = end_time - start_time
                    # Note: le seed est déjà dans grid_data via get_grid_data()
                    results['generated_grids'].append(grid_data)
                    print(" Succès.")
                else:
                    results['failures'] += 1
                    print(" Échec (grille vide).")
            else:
                results['failures'] += 1
                print(" Échec (génération impossible).")
        
        except TimeoutException as e:
            results['timeouts'] += 1
            print(f" Échec ({e})")
        except Exception as e:
            results['failures'] += 1
            logging.error(f"\nErreur inattendue lors de la génération (seed {i}):", exc_info=True)
            print(f" Échec CRITIQUE ({e})")
            
    return results

def generate_html_report(all_results):
    """Génère un fichier report.html."""
    html = """
    <html>
    <head>
        <title>Rapport de Génération de Grilles</title>
        <meta charset="UTF-8">
        <style>
            body { font-family: sans-serif; margin: 2em; background-color: #f8f9fa; }
            h1, h2 { color: #343a40; border-bottom: 1px solid #dee2e6; padding-bottom: 10px; }
            .report-summary { background-color: #e9ecef; padding: 1em; border-radius: 5px; margin-bottom: 2em; }
            .grid-container { display: flex; flex-wrap: wrap; gap: 2em; }
            .grid-item { background-color: white; padding: 1em; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            table { border-collapse: collapse; }
            td { border: 1px solid #ccc; width: 25px; height: 25px; text-align: center; vertical-align: middle; font-weight: bold; font-size: 12px; }
            .black { background-color: #343a40; }
        </style>
    </head>
    <body>
        <h1>Rapport de Génération de Grilles</h1>
        <p>Généré le: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
    """

    for batch_result in all_results:
        config = batch_result['config']
        grids = batch_result['generated_grids']
        width, height, count = config['width'], config['height'], config['count']
        
        html += f"<h2>Batch: {len(grids)} / {count} Grilles de {width}x{height}</h2>"
        
        if grids:
            times = [g['generation_time'] for g in grids]
            ratios = [g['fill_ratio'] for g in grids]
            avg_time_ms = statistics.mean(times) * 1000
            avg_ratio_percent = statistics.mean(ratios) * 100
            
            html += f"""
            <div class="report-summary">
                <strong>Temps moyen:</strong> {avg_time_ms:.0f} ms | 
                <strong>Remplissage moyen:</strong> {avg_ratio_percent:.1f}%
            </div>
            """

        html += '<div class="grid-container">'
        for grid_data in grids:
            html += f"""
            <div class="grid-item">
                <p>Seed: {grid_data['seed']} | Remplissage: {grid_data['fill_ratio']*100:.1f}% | Temps: {grid_data['generation_time']*1000:.0f}ms</p>
                <table><tbody>
            """
            rows = [[] for _ in range(grid_data['height'])]
            for cell in grid_data['cells']:
                rows[cell['y']].append(cell)
            
            for row in rows:
                html += "<tr>"
                for cell in row:
                    class_name = "black" if cell['is_black'] else ""
                    char = cell['char'] or ''
                    html += f'<td class="{class_name}">{char}</td>'
                html += "</tr>"

            html += "</tbody></table></div>"
        html += "</div>"

    html += "</body></html>"
    
    report_path = "report.html"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n\nRapport HTML généré : {os.path.abspath(report_path)}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
    all_words = load_all_words()
    if all_words:
        all_results = []
        for config in TEST_CONFIGS:
            test_results = run_test_batch(all_words, config)
            all_results.append(test_results)
        generate_html_report(all_results)