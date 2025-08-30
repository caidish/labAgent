from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="lab-agent",
    version="0.1.0",
    author="Lab Agent Team",
    author_email="contact@example.com",
    description="A multi-agent system for laboratory automation and research",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/caijiaqi/labAgent",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "lab-agent=lab_agent.main:main",
            "lab-agent-web=lab_agent.web:main",
        ],
    },
)