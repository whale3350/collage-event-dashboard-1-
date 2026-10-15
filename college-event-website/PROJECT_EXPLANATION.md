# Project explanation

**Title:** Campusly — College Event Website with Student Performance Predictor  
**Domain:** Backend & Cloud Computing

Campusly is a web-based college event platform that helps students discover campus activities and track their participation. The dashboard showcases upcoming events, registrations, involvement categories, and recent activity. A REST API built with FastAPI provides event CRUD operations, registration endpoints, aggregate statistics, and a student performance estimate. SQLite persists event and registration records locally.

The performance predictor currently uses a transparent weighted formula from attendance, previous marks, study hours, and assignment completion. It is included to demonstrate the API flow and should be labelled an illustrative estimate until a real dataset-backed model is trained and evaluated. The project can be extended with authentication, PostgreSQL, automated tests, and cloud deployment.
