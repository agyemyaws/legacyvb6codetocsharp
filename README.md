# Legacy Code to C# Translation Pipeline

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

An intelligent pipeline for translating legacy VB6 applications to modern C# using AI-powered multi-agent translation with RAG-enhanced context retrieval.

## 🚀 Key Features

- **Multi-Agent Translation**: Specialized agents for forms, business logic, and data access
- **RAG-Enhanced Context**: Retrieval-augmented generation using VB6-to-C# pattern knowledge base
- **Intelligent Analysis**: Dependency resolution and complexity analysis of VB6 projects
- **Complete C# Projects**: Generates ready-to-build .NET solutions with proper structure
- **Modern Patterns**: Converts legacy patterns to modern C# equivalents (ADODB → EF Core)

## 🏛️ Architecture

```
VB6 Project → Analysis → Multi-Agent Translation → Validation → C# Solution
```

**Project Structure:**
```
├── Core/                    # Analysis and orchestration
├── Translation/Agents/      # Specialized translation agents
├── Knowledge/              # RAG patterns and rules
├── Evaluation/             # Quality validation
└── Data/                   # Input/Output projects
```

## 🛠️ Installation

**Prerequisites:** Python 3.8+, Git, and either Ollama (local) or Claude API access

1. **Clone and setup**:
```bash
git clone https://github.com/yourusername/LegacyCodeToCSharp.git
cd LegacyCodeToCSharp
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure AI Provider**:
```bash
# For Ollama (local)
ollama pull codellama:latest

# For Claude API
cp env.example .env
# Add your API key to .env file
```

## 📖 Usage

**Basic translation**:
```bash
python main.py Data/Input/BMI/bmi.vbp
```

**With custom output**:
```bash
python main.py Data/Input/BMI/bmi.vbp --output-dir MyProject --strategy modernizing
```

**Analyze project first**:
```bash
python Core/analyzer.py Data/Input/BMI
```

## 📁 Generated Project Structure

```
MyTranslatedProject/
├── MyTranslatedProject.sln
├── MyTranslatedProject.csproj
├── Program.cs
├── Forms/                  # Translated VB6 forms
├── Models/                 # Business objects  
├── Services/               # Data access & business logic
└── Utils/                  # Helper classes
```

## 🔧 Configuration

**Command Line Options:**
- `--output-dir MyProject` - Custom output directory
- `--strategy modernizing` - Translation strategy (conservative/modernizing/parallel)
- `--max-workers 4` - Parallel processing threads
- `--verbose` - Detailed logging

**Environment Variables (.env file):**
```env
DEFAULT_PROVIDER=claude
CLAUDE_API_KEY=your_api_key_here
OLLAMA_BASE_URL=http://localhost:11434
```

## 🚀 Building Translated Projects

```bash
cd MyTranslatedProject
dotnet restore
dotnet build
dotnet run
```

## 🔍 Translation Agents

| VB6 File Type | Agent | C# Output |
|---------------|-------|-----------|
| `.frm` (Forms) | Form Agent | WinForms with Designer |
| `.cls` (Classes) | Business Logic Agent | C# Classes |
| `.bas` (Modules) | Business Logic Agent | Static Classes |
| Database Code | Data Access Agent | Entity Framework |

## 🧪 Testing

```bash
# Run tests
python -m pytest Test/

# Validate translated code
python Evaluation/evaluator.py MyTranslatedProject/
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/name`
3. Make changes and add tests
4. Run tests: `python -m pytest`
5. Submit a Pull Request


## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

<div align="center">

**⭐ Star this repository if you find it helpful!**

</div>

