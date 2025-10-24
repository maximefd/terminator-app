import logging
from .grid_template import GridTemplate

class SlotFinder:
    """
    Analyse un GridTemplate pour trouver tous les emplacements de mots (slots)
    valides (longueur > 1) et calculer leurs contraintes.
    """
    def __init__(self, template: GridTemplate):
        self.template = template
        self.width = template.width
        self.height = template.height
        self.slots = []
        self.intersections = {}

    def find_all_slots(self) -> list[dict]:
        """
        Méthode principale pour trouver et trier tous les slots.
        """
        logging.info("Début de la recherche des slots...")
        covered_h = [[False for _ in range(self.width)] for _ in range(self.height)]
        covered_v = [[False for _ in range(self.width)] for _ in range(self.height)]
        slot_id_counter = 0

        for y in range(self.height):
            for x in range(self.width):
                if self.template.is_black_square(x, y):
                    continue

                # --- Trouver les slots horizontaux ---
                if not covered_h[y][x] and (x == 0 or self.template.is_black_square(x - 1, y)):
                    length = 0
                    while x + length < self.width and not self.template.is_black_square(x + length, y):
                        self._add_intersection(x + length, y)
                        covered_h[y][x + length] = True
                        length += 1
                    
                    # LA CORRECTION EST ICI : On n'ajoute que les slots de plus d'une lettre
                    if length > 1:
                        self.slots.append(self._create_slot_entry(slot_id_counter, x, y, 'across', length))
                        slot_id_counter += 1

                # --- Trouver les slots verticaux ---
                if not covered_v[y][x] and (y == 0 or self.template.is_black_square(x, y - 1)):
                    length = 0
                    while y + length < self.height and not self.template.is_black_square(x, y + length):
                        self._add_intersection(x, y + length)
                        covered_v[y + length][x] = True
                        length += 1
                    
                    # LA CORRECTION EST ICI : On n'ajoute que les slots de plus d'une lettre
                    if length > 1:
                        self.slots.append(self._create_slot_entry(slot_id_counter, x, y, 'down', length))
                        slot_id_counter += 1
        
        self._calculate_all_constraints()
        self.slots.sort(key=lambda s: s['constraints'], reverse=True)
        logging.info(f"{len(self.slots)} slots valides (longueur > 1) trouvés et triés.")
        return self.slots

    def _add_intersection(self, x, y):
        coord = (x, y)
        self.intersections[coord] = self.intersections.get(coord, 0) + 1

    def _create_slot_entry(self, id, x, y, direction, length):
        return {
            'id': id,
            'x': x,
            'y': y,
            'direction': direction,
            'length': length,
            'constraints': 0
        }

    def _calculate_all_constraints(self):
        for slot in self.slots:
            count = 0
            for i in range(slot['length']):
                x = slot['x'] + i if slot['direction'] == 'across' else slot['x']
                y = slot['y'] if slot['direction'] == 'across' else slot['y'] + i
                
                if self.intersections.get((x, y), 0) > 1:
                    count += 1
            slot['constraints'] = count
