"use strict";

document.getElementById("login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const error = document.getElementById("login-error");
  const pin = document.getElementById("pin");
  error.textContent = "";
  try {
    const response = await fetch("/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pin: pin.value }),
    });
    if (response.ok) {
      window.location.href = "/";
      return;
    }
    const data = await response.json().catch(() => ({}));
    error.textContent = data.error || "Connexion impossible.";
  } catch {
    error.textContent = "Le curateur ne répond pas. Est-il lancé (make curator) ?";
  }
  pin.select();
});
