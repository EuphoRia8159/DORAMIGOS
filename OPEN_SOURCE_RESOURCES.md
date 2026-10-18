# DORAMIGOS / AEGIS — Open-Source Resources & Data Attribution

This page lists the open-source software dependencies declared by this repository and the public dataset source discussed for the hospital directory. See [requirements.txt](https://github.com/EuphoRia8159/DORAMIGOS/blob/main/requirements.txt) for the project's declared Python packages.

## Open-source software dependencies

- [Python](https://www.python.org/) — programming language/runtime.
- [Streamlit](https://streamlit.io/) — interactive Python frontend.
- [pandas](https://pandas.pydata.org/) — tabular data handling.
- [Requests](https://requests.readthedocs.io/) — HTTP client.
- [FastAPI](https://fastapi.tiangolo.com/) — backend API framework.
- [Uvicorn](https://www.uvicorn.org/) — ASGI server.
- [SQLAlchemy](https://www.sqlalchemy.org/) — database toolkit/ORM.
- [Pydantic](https://docs.pydantic.dev/) — data validation and settings models.
- [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) — settings management.
- [HTTPX](https://www.python-httpx.org/) — HTTP client used by the integration layer.
- [pytest](https://docs.pytest.org/) — test framework.
- [openpyxl](https://openpyxl.readthedocs.io/) — Excel workbook support.

The frontend also includes project-owned HTML, CSS, and JavaScript under [static/](https://github.com/EuphoRia8159/DORAMIGOS/tree/main/static). The standard-library SQLite support is part of Python rather than a separately installed package.

## Public data source

- [Government of India Open Government Data Platform — National Hospital Directory with Geo Code and additional parameters](https://www.data.gov.in/resource/national-hospital-directory-geo-code-and-additional-parameters-updated-till-last-month)

The project team has referenced a cleaned hospital-directory CSV supplied by a teammate. Please retain the source attribution above and check the dataset page's current terms/usage conditions before redistributing the data. Dataset contents and freshness should be independently verified before real-world use.

## Deployment and integration notes

- [DORAMIGOS / AEGIS source repository](https://github.com/EuphoRia8159/DORAMIGOS)
- [Render](https://render.com/) is the hosting platform; it is a service, not an open-source dependency of the application.
- IBM Z integration in this deployed demo is configured for mock/sandbox simulation. Do not describe this as a live IBM Z or live hospital-system connection.

## Safety note

AEGIS is a demonstration prototype, not a clinically validated medical system. Do not use it for real-world triage, patient care, or emergency dispatch.
