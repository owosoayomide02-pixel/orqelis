# Subprocessor policy (draft)

Effective: 2026-09-15  
Owner: [LEGAL ENTITY NAME]  
Status: V2 draft. Not a customer contract until legal review.

Orqelis may use subprocessors to host the control plane, send email, or run the AI gateway. Current development defaults:

- Database: local SQLite, or PostgreSQL if the operator deploys it
- Email: development log backend, or operator-configured SMTP
- AI: operator-configured OpenAI-compatible provider (for example Groq)

Production subprocessors must be listed here with purpose, location, and a contact for [PRIVACY EMAIL] before customer data is processed.

This document does not claim SOC 2, ISO 27001, or NDPR certification.
