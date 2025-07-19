from setuptools import setup, find_packages

setup(
    name="llm_testcase",
    version="0.1.0",
    packages=find_packages(),
    python_requires=">=3.8,<3.10",
    install_requires=[
        "pytest",
        "pytest-xdist",
        "pydantic",
        "chromadb==0.5.4",
        "openai",
        "langchain-openai",
        "langchain-core",
        "langchain-community",
        "python-docx",
        "pdfplumber",
        "numpy==1.24.4",
        "pandas",
        "requests",
        "jsonschema",
        "rich",
        "pytest-repeat",
        "beautifulsoup4"
    ],
)