import { useState, useEffect } from "react";

// Ce hook prend une valeur (ce que l'utilisateur tape) et un délai
export function useDebounce<T>(value: T, delay?: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    // Met en place un minuteur
    const timer = setTimeout(() => {
      setDebouncedValue(value); // Met à jour la valeur "debounced" après le délai
    }, delay || 500); // 500ms par défaut

    // Nettoie le minuteur si la valeur change (l'utilisateur tape une nouvelle lettre)
    return () => {
      clearTimeout(timer);
    };
  }, [value, delay]);

  return debouncedValue;
}