# 🧩 Terminator - Outil d'aide à la création de grilles de mots fléchés

## 📝 Description

Terminator est une application web conçue pour les créateurs de grilles de mots fléchés, qu'ils soient amateurs, auteurs ou éditeurs. L'objectif est d'offrir un outil professionnel pour remplir automatiquement des grilles avec des mots cohérents, en respectant des contraintes de lettres et en s'appuyant sur des dictionnaires personnels et globaux.

Ce n'est **pas** un jeu, mais un **outil de création**.

## 🛠️ Stack Technique

* **Frontend**: Next.js 15 (App Router), TypeScript, TailwindCSS, shadcn/ui, React Query, Zustand
* **Backend**: Flask, SQLAlchemy, Python 3.11+
* **Base de données**: PostgreSQL 15+
* **Moteur de recherche**: Trie custom en mémoire pour le dictionnaire global (DELA)
* **Environnement**: Docker & Docker Compose

## ✅ Prérequis

Avant de commencer, assurez-vous d'avoir installé les outils suivants :

* [Git](https://git-scm.com/downloads)
* [Docker Desktop](https://www.docker.com/products/docker-desktop/)
* Un éditeur de code, comme [VS Code](https://code.visualstudio.com/)

## 🚀 Démarrage Rapide

1.  Clonez ce dépôt.
2.  Assurez-vous que Docker Desktop est en cours d'exécution.
3.  Lancez l'application avec la commande suivante à la racine du projet :
    ```bash
    docker compose up --build
    ```
4.  Ouvrez votre navigateur :
    * Frontend : `http://localhost:3000`
    * Backend API : `http://localhost:5000`

## 📂 Structure du Projet

Le projet utilise une architecture monorepo :
terminator-app/
├── backend/        # API Flask, moteur de recherche, logique métier
├── frontend/       # Application Next.js (UI)
├── docs/           # Documentation technique (ADR, etc.)
└── docker-compose.yml # Fichier d'orchestration Docker

