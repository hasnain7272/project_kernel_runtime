"""
Setup script for observability components.
"""

from setuptools import setup, find_packages

setup(
    name="project-kernel-runtime-observability",
    version="1.0.0",
    description="Observability components for Project Kernel Runtime",
    author="Project Kernel Runtime Team",
    author_email="team@projectkernel.ai",
    packages=find_packages(),
    install_requires=[
        "opentelemetry-api>=1.20.0",
        "opentelemetry-sdk>=1.20.0",
        "opentelemetry-exporter-otlp>=1.20.0",
        "opentelemetry-exporter-jaeger>=1.20.0",
        "opentelemetry-exporter-zipkin>=1.20.0",
        "opentelemetry-instrumentation>=0.40b0",
        "fastapi>=0.100.0",
        "uvicorn>=0.23.0",
        "pydantic>=2.0.0",
        "aiofiles>=23.0.0",
        "structlog>=23.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)