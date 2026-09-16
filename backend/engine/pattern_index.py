"""
Index des mots d'une même longueur par (position, lettre), sous forme d'ensembles de bits (#20).

Remplace le parcours du Trie par motif dans le solveur : les candidats d'un motif sont le ET binaire
des ensembles de ses lettres connues. Le bit n°i représente `words[i]` ; un ensemble est un entier Python.
Compter les candidats (choix du slot, forward checking) ne demande qu'un `bit_count()`, et il n'y a plus
de cache à invalider. Pur : aucune lecture de fichier, aucun état global.
"""

# Positions des bits à 1 de chaque octet (0 à 255), pour extraire vite les mots d'un ensemble
_BITS_OF_BYTE = [tuple(bit for bit in range(8) if value >> bit & 1) for value in range(256)]


class PatternIndex:
    def __init__(self, words: list[str]):
        """`words` : mots de même longueur, dans l'ordre où les candidats doivent être rendus."""
        self.words = list(words)
        self.length = len(self.words[0]) if self.words else 0
        self.position = {word: i for i, word in enumerate(self.words)}
        self.full_mask = (1 << len(self.words)) - 1
        self._nbytes = (len(self.words) + 7) // 8

        # Construction octet par octet : bien plus rapide que des OU successifs sur de grands entiers
        buffers: dict[tuple[int, str], bytearray] = {}
        for i, word in enumerate(self.words):
            byte, bit = i >> 3, 1 << (i & 7)
            for pos, char in enumerate(word):
                buffer = buffers.get((pos, char))
                if buffer is None:
                    buffer = buffers[(pos, char)] = bytearray(self._nbytes)
                buffer[byte] |= bit
        self._masks = {key: int.from_bytes(buffer, "little") for key, buffer in buffers.items()}

    def mask(self, pattern: str) -> int:
        """Ensemble des mots qui correspondent au motif (`?` = lettre inconnue)."""
        result = self.full_mask
        for pos, char in enumerate(pattern):
            if char != "?":
                result &= self._masks.get((pos, char), 0)
                if not result:
                    break
        return result

    def mask_of(self, words) -> int:
        """Ensemble des mots donnés (les mots absents de l'index sont ignorés)."""
        buffer = bytearray(self._nbytes)
        for word in words:
            i = self.position.get(word)
            if i is not None:
                buffer[i >> 3] |= 1 << (i & 7)
        return int.from_bytes(buffer, "little")

    def bit(self, word: str) -> int:
        """Ensemble réduit à ce mot (0 si le mot n'est pas dans l'index)."""
        i = self.position.get(word)
        return 0 if i is None else 1 << i

    def words_in(self, mask: int) -> list[str]:
        """Mots d'un ensemble, dans l'ordre de l'index."""
        words = self.words
        result = []
        for byte_index, byte in enumerate(mask.to_bytes(self._nbytes, "little")):
            if byte:
                base = byte_index << 3
                for bit in _BITS_OF_BYTE[byte]:
                    result.append(words[base + bit])
        return result
