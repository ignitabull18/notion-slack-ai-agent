from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="notion-slack-agent",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="AI-powered integration between Notion and Slack using Agno framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ignitabull18/notion-slack-ai-agent",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.4",
            "pytest-asyncio>=0.21.1",
            "pytest-cov>=4.1.0",
            "black>=24.1.0",
            "flake8>=7.0.0",
            "mypy>=1.8.0",
            "pre-commit>=3.6.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "notion-slack-agent=src.main:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)