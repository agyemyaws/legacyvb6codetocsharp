# Legacy Code to C# Translation Pipeline

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

An intelligent pipeline for translating legacy VB6 applications to modern C# using LLM-powered multi-agent translation with RAG-enhanced context retrieval.

## 🚀 Key Features

- **Multi-Agent Translation**: Specialized agents for forms, business logic, and data access
- **Syntax Solver & Optimization**: Post-translation syntax fixing and code optimization
- **RAG-Enhanced Context**: Retrieval-augmented generation using VB6-to-C# pattern knowledge base
- **Intelligent Analysis**: Dependency resolution and complexity analysis of VB6 projects
- **Complete C# Projects**: Generates ready-to-build .NET solutions with proper structure
- **Modern Patterns**: Converts legacy patterns to modern C# equivalents (ADODB → EF Core)

## 🏛️ Architecture

```
VB6 Project → Analysis → Multi-Agent Translation → Syntax Optimization → Validation → C# Solution
```

**Project Structure:**
```
├── Core/                    # Analysis and orchestration
│   ├── analyzer.py         # VB6 project analysis
│   └── project_orchestrator.py # Main translation coordinator
├── Translation/Agents/      # Specialized translation agents
│   ├── form_agent.py       # VB6 forms → C# WinForms
│   ├── business_logic_agent.py # VB6 modules/classes → C# classes
│   └── syntax_solver_and_optimization_agent.py # Post-processing
├── Knowledge/              # RAG patterns and rules
│   ├── rag_manager.py      # Pattern retrieval system
│   └── VB6_to_CSharp_Equivalents/ # Pattern knowledge base
├── Utils/                  # Helper utilities
├── Evaluation/             # Quality validation framework
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
python main.py Data/Input/BMI/bmi.vbp --output-dir MyProject
```

**Analyze project first**:
```bash
python Core/analyzer.py Data/Input/BMI
```

## 📁 Generated Project Structure

The pipeline generates complete .NET 8 WinForms projects with modern C# patterns:

```
MyTranslatedProject/
├── MyTranslatedProject.sln          # Visual Studio solution file
├── MyTranslatedProject.csproj       # .NET 8 project file with EF Core
├── README.md                        # Translation summary and notes
└── MyTranslatedProject/             # Translated source files
    ├── FormName.cs                  # Translated forms (main code)
    ├── FormName.Designer.cs         # Designer files (UI layout)
    ├── ClassName.cs                 # Business logic classes
    └── translation_summary.txt      # Detailed translation report
```

**Key Features:**
- **.NET 8 WinForms** with modern project structure
- **Entity Framework Core** for data access (replaces ADODB)
- **Proper namespacing** and C# conventions
- **Designer files** for form layouts
- **Translation summary** with metrics and optimization details

## 🤖 Translation Agents

The pipeline uses specialized AI agents for different aspects of translation:

### Core Translation Agents
- **FormAgent**: Converts VB6 forms (.frm) to C# WinForms with proper control mapping and event handling
- **BusinessLogicAgent**: Translates VB6 modules (.bas) and classes (.cls) to modern C# classes with proper data access patterns

### Post-Processing Agent
- **SyntaxSolverAndOptimizationAgent**: 
  - Fixes compilation errors and syntax issues in translated code
  - Applies modern C# naming conventions and patterns
  - Optimizes performance (string interpolation, LINQ, efficient collections)
  - Ensures code follows C# best practices and is production-ready
  - Preserves original VB6 functionality while modernizing implementation

Each translated file goes through the optimization process automatically to ensure high-quality, maintainable C# code.

## 🔧 Configuration

**Command Line Options:**
- `--output-dir MyProject` - Custom output directory
- `--max-workers 4` - Parallel processing threads
- `--verbose` - Detailed logging
- `--log-file` - Write log output to specific file

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

## 🔍 RAG Knowledge Base

The pipeline includes a comprehensive knowledge base of VB6-to-C# translation patterns:

**Pattern Categories:**
- **Business Logic Patterns**: Module and class translations
- **Forms Patterns**: WinForms control mappings and event handling
- **Data Access Patterns**: ADODB to Entity Framework conversions
- **Error Handling Patterns**: VB6 error handling to C# exceptions
- **COM Patterns**: Component Object Model translations

**RAG Manager Usage:**
```bash
# View knowledge base statistics
python Knowledge/rag_manager.py --action stats

# Search for patterns
python Knowledge/rag_manager.py --action search --query "VB6 code here"

# Load patterns from JSON files
python Knowledge/rag_manager.py --action load
```

## 🔍 Translation Agents

| VB6 File Type | Agent | C# Output |
|---------------|-------|-----------|
| `.frm` (Forms) | Form Agent | WinForms with Designer |
| `.cls` (Classes) | Business Logic Agent | C# Classes |
| `.bas` (Modules) | Business Logic Agent | Static Classes |
| All Files | Syntax Solver & Optimization Agent | Optimized, production-ready C# |

## 🧪 Testing

```bash
# Run tests
python -m pytest Test/

# Analyze VB6 project structure
python Core/analyzer.py Data/Input/YourProject

# Test translation orchestrator directly
python Core/project_orchestrator.py Data/Input/YourProject --output-dir TestOutput
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/name`
3. Make changes and add tests
4. Run tests: `python -m pytest`
5. Submit a Pull Request

## 🆘 Support

**Common Issues:**
- **Translation fails**: Check VB6 project file (.vbp) is valid
- **Missing dependencies**: Ensure all referenced VB6 files exist
- **AI provider errors**: Verify API keys or Ollama installation
- **RAG patterns not loading**: Check ChromaDB installation and embeddings model
- **Optimization agent fails**: Verify model client configuration


## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

<div align="center">

**⭐ Star this repository if you find it helpful!**

</div>

