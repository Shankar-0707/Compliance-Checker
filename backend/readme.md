# 📂 Project Structure
```
backend/
│
├── app/
│   ├── core/              # Configuration, logging
│   │   └── config.py      # Environment variables
│   │
│   ├── db/                # Database setup
│   │   ├── session.py     # Async session
│   │   └── base.py        # Base model (metadata)
│   │
│   ├── models/            # SQLAlchemy models
│   │   ├── user.py
│   │   └── compliance.py
│   │
│   ├── schemas/           # Pydantic request/response schemas
│   │   ├── user.py
│   │   └── compliance.py
│   │
│   ├── services/          # Business logic
│   │   ├── user_service.py
│   │   └── compliance_service.py
│   │
│   ├── routers/           # API endpoint definitions
│   │   ├── auth.py
│   │   ├── users.py
│   │   └── compliance.py
│   │
│   ├── main.py            # Application entry point
│   └── wsgi.py            # For render.com deployment
│
├── tests/                 # Unit tests
│
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (not in git)
└── Dockerfile             # Containerization
``` 