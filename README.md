# Parser SQL - Mini Gestor de Bases de Datos

Este directorio contiene el código fuente del backend de la aplicación, desarrollado con Node.js y Express. Aquí se gestionan las rutas, controladores, modelos y la lógica de negocio.

# 🧠 Proyecto Backend BD2 — Mini Gestor de Bases de Datos Multimodal

### 📚 CS2702 - Base de Datos II | Universidad de Ingeniería y Tecnología (UTEC)

---

## 👥 Integrantes

| N° | Nombre Completo |
|----|------------------|
| 1 | **Chilo Gonzalez, Jhon Erick** |
| 2 | **Mercado Barbieri, Ariana Valeria** |
| 3 | **Gianfranco Gonzalo Cordero Aguirre** |
| 4 | **Huamani Ñaupas, Jose Eduardo** |
| 5 | **Iribar Casanova, Federico** |

---

## 🚀 Objetivo General

Diseñar e implementar un **sistema de base de datos multimodal** capaz de **indexar y consultar datos estructurados y no estructurados**, integrando **técnicas de indexación avanzada**.  

El proyecto busca construir una **API backend** que funcione como un **mini gestor de bases de datos**, conectada a un **frontend ligero** y capaz de manejar diversos tipos de datos (texto, imágenes, audio, video, datos tabulares).

---

## 🏗️ Arquitectura General del Proyecto

### 🔹 Backend (API de Minigestor Multimodal)
- Parser SQL personalizado (traduce consultas SQL-like a un plan interno).  
- Query Engine (motor de ejecución con optimizador).  
- Módulo de almacenamiento tabular con índices: `Sequential File`, `ISAM`, `B+Tree`, `Extendible Hashing`.  
- Módulo vectorial con soporte para embeddings (`R-Tree`, `k-NN`, IVF Flat / PQ).  
- Persistencia en disco de archivos, índices y metadatos.  
- Gestión de logs y operaciones CRUD.  

### 🔹 Frontend (UI Cliente)
Interfaz web ligera desarrollada en React o Flask/Django, que permite:
- Enviar consultas SQL personalizadas al backend.  
- Visualizar resultados tabulares.  
- Subir archivos CSV, imágenes o audio para indexación.  
- Explorar estructuras de índices visualmente.  

### 🔹 Capa de Aplicaciones
Aplicaciones conectadas al backend:
- 🏭 Sistema de gestión de inventarios (búsqueda por nombre, código o ubicación).  
- 🌍 Sistema de gestión geoespacial (rutas, estaciones, puntos de interés).  
- 🤖 Aplicaciones de IA (reconocimiento facial, detección de audio duplicado, recomendación de noticias o productos).  

---

## 🧩 Técnicas de Indexación Implementadas

| Técnica | Tipo de Datos | Operaciones Soportadas |
|----------|----------------|------------------------|
| Sequential File | Tabulares | `search`, `rangeSearch`, `add` |
| ISAM-Sparse Index | Tabulares | `search`, `rangeSearch`, `add` |
| Extendible Hashing | Tabulares | `search`, `add`, `remove` |
| B+Tree | Tabulares | `search`, `rangeSearch`, `add`, `remove` |
| R-Tree | Espaciales | `spatialRangeSearch`, `rangeSearch(point, radio)` |

> 💡 Cada índice incluye algoritmos optimizados para inserción, búsqueda y eliminación, reduciendo accesos a disco.

---

## 🧠 Parser SQL Personalizado

El sistema incluye un **parser SQL completo**, con análisis **léxico**, **sintáctico** y **semántico**, capaz de traducir consultas SQL-like a operaciones del gestor.

### 🧱 Estructura del módulo
