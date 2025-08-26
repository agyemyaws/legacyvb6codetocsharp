# Legacy Code to C# Translation Pipeline

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![CI](https://github.com/yourusername/LegacyCodeToCSharp/workflows/CI/badge.svg)](https://github.com/yourusername/LegacyCodeToCSharp/actions)
[![Issues](https://img.shields.io/github/issues/yourusername/LegacyCodeToCSharp)](https://github.com/yourusername/LegacyCodeToCSharp/issues)
[![Stars](https://img.shields.io/github/stars/yourusername/LegacyCodeToCSharp)](https://github.com/yourusername/LegacyCodeToCSharp/stargazers)

A comprehensive, enterprise-grade pipeline for translating legacy VB6 and Fortran applications to modern C# with intelligent analysis, multi-agent translation, and automated project generation.

## 🚀 Key Features

### 🔄 Multi-Agent Translation System
- **Business Logic Agent**: Transforms VB6/Fortran classes and modules to C# services
- **Form Translation Agent**: Converts VB6 forms to modern WinForms with proper event handling
- **Data Access Agent**: Migrates ADODB patterns to Entity Framework Core
- **Integration Agent**: Handles COM objects and external dependencies
- **Syntax Solver Agent**: Resolves complex language-specific constructs

### 🧠 Intelligent Analysis Engine
- **Deep Code Analysis**: Comprehensive parsing of VB6 projects (.vbp, .frm, .cls, .bas)
- **Dependency Resolution**: Smart ordering of translation based on file dependencies
- **External Dependencies Detection**: Identifies COM objects, DLLs, and OCX controls
- **Code Complexity Metrics**: Calculates maintainability and complexity scores
- **Translation Strategy Planning**: Recommends optimal approaches for complex scenarios

### 🏗️ Modern C# Project Generation
- **Complete Project Structure**: Generates .sln, .csproj, Program.cs, and organized folders
- **WinForms .NET Support**: Full support for modern WinForms applications
- **Entity Framework Integration**: Automatic database layer generation with EF Core
- **Best Practices**: Follows modern C# conventions and patterns
- **NuGet Package Management**: Automatic dependency resolution and package references

## 🏛️ Architecture

### Translation Pipeline
```
Input (VB6/Fortran) → Analysis → Decomposition → Multi-Agent Translation → Validation → C# Project
```

### Project Structure
```
├── Core/                    # Analysis and orchestration engine
├── Translation/             # Multi-agent translation system
│   └── Agents/             # Specialized translation agents
├── Evaluation/             # Quality assurance and validation
├── Knowledge/              # RAG patterns and translation rules
├── Utils/                  # Utilities and helpers
├── Config/                 # Configuration files
└── Data/                   # Input/Output projects
```

### Supported Translation Patterns
- **Forms**: VB6 Forms → WinForms with designer support
- **Classes**: VB6 Classes → C# classes with proper encapsulation
- **Modules**: VB6 Modules → C# static classes
- **Data Access**: ADODB → Entity Framework Core
- **COM Objects**: ActiveX controls → .NET equivalents

## 🛠️ Installation

### Prerequisites
- Python 3.8 or higher
- Git
- Either Ollama (local) or Claude API access

### Quick Start

1. **Clone the repository**:
```bash
git clone https://github.com/yourusername/LegacyCodeToCSharp.git
cd LegacyCodeToCSharp
```

> **Note**: Replace `yourusername` with your actual GitHub username after forking

2. **Set up Python environment**:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

3. **Configure AI Provider** (choose one):

**Option A: Local Ollama** (Recommended for privacy)
```bash
# Install Ollama from https://ollama.ai/
ollama pull codellama:7b
```

**Option B: Claude API**
```bash
# Copy environment template
cp env.example .env
# Edit .env and add your Claude API key
echo "CLAUDE_API_KEY=your_api_key_here" >> .env
echo "DEFAULT_PROVIDER=claude" >> .env
```

## 📖 Usage

### Basic Translation

**Translate a VB6 project**:
```bash
python main.py Data/Input/BMI/bmi.vbp
```

**Translate with custom output directory**:
```bash
python main.py Data/Input/BMI/bmi.vbp --output-dir MyTranslatedProject
```

**Advanced translation with parallel processing**:
```bash
python main.py Data/Input/BMI/bmi.vbp \
  --strategy parallel \
  --max-workers 4 \
  --verbose
```

### Translation Strategies

| Strategy | Description | Best For |
|----------|-------------|----------|
| `conservative` | Minimal changes, direct translation | Critical systems, exact behavior preservation |
| `modernizing` | Modern C# patterns and practices | General purpose, recommended default |
| `incremental` | Step-by-step with validation | Large, complex projects |
| `parallel` | Multi-threaded processing | High-performance translation |

### Project Analysis

**Analyze VB6 project structure**:
```bash
python Core/analyzer.py Data/Input/BMI
```

**Example Analysis Output:**
```
🔍 Project Analysis: BMI Calculator
═══════════════════════════════════
📁 Files: 4 | 📊 Total LOC: 500 | 🎯 Complexity: 45

📋 Translation Order:
  1. CPerson.cls (class) - No dependencies
  2. modDatabase.bas (module) - Uses ADODB
  3. modUtilities.bas (module) - No dependencies  
  4. mainfrm.frm (form) - Uses all above files

🔗 External Dependencies:
  • ADODB.Connection (COM object)
  • ADODB.Recordset (COM object)
  
💡 Recommended Strategy: modernizing
```

## 📁 Generated Project Structure

The pipeline creates a complete, modern C# solution:

```
MyTranslatedProject/
├── MyTranslatedProject.sln          # Visual Studio solution
├── MyTranslatedProject.csproj       # Project file with dependencies
├── Program.cs                       # Application entry point
├── Forms/                          # WinForms UI components
│   ├── MainForm.cs                 # Translated forms
│   └── MainForm.Designer.cs        # Designer code
├── Models/                         # Data models and entities
│   ├── Person.cs                   # Business objects
│   └── DatabaseModels.cs           # Data access models
├── Services/                       # Business logic layer
│   ├── DatabaseService.cs          # Data access service
│   └── BusinessLogicService.cs     # Core business logic
├── Utils/                          # Utility classes
│   └── Helpers.cs                  # Helper functions
└── Resources/                      # Application resources
    └── app.config                  # Configuration
```

## 🔧 Configuration Options

### Command Line Arguments

| Option | Description | Example |
|--------|-------------|---------|
| `--output-dir` | Custom output directory | `--output-dir MyProject` |
| `--strategy` | Translation strategy | `--strategy modernizing` |
| `--max-workers` | Parallel processing threads | `--max-workers 4` |
| `--verbose` | Detailed logging | `--verbose` |
| `--quiet` | Minimal output | `--quiet` |
| `--log-file` | Custom log file path | `--log-file my.log` |

### Environment Configuration

Create a `.env` file for custom settings:

```env
# AI Provider Configuration
DEFAULT_PROVIDER=claude                    # or "ollama"
CLAUDE_API_KEY=your_claude_api_key_here
OLLAMA_BASE_URL=http://localhost:11434

# Model Settings
CLAUDE_MODEL=claude-3-sonnet-20240229
OLLAMA_MODEL=codellama:7b

# Translation Settings
MODEL_CACHE_DIR=/path/to/cache
```

## 🚀 Building and Running Translated Projects

After translation, your C# project is ready to build:

```bash
cd MyTranslatedProject

# Restore NuGet packages
dotnet restore

# Build the project
dotnet build

# Run the application
dotnet run
```

## 📋 Examples

### Example 1: BMI Calculator (Included)

Translate the included BMI calculator example:

```bash
python main.py Data/Input/BMI/bmi.vbp --output-dir BMI_Translated
```

### Example 2: Large Enterprise Application

For complex applications with many dependencies:

```bash
python main.py Data/Input/MyLargeApp/app.vbp \
  --strategy incremental \
  --max-workers 6 \
  --verbose \
  --output-dir MyLargeApp_CSharp
```

### Example 3: Batch Processing Multiple Projects

Process multiple VB6 projects:

```bash
# Process all .vbp files in a directory
find Data/Input -name "*.vbp" -exec python main.py {} \;
```

## 🔍 Translation Patterns

The system uses specialized AI agents and patterns for different code types:

| File Type | Agent | Output | Specialization |
|-----------|-------|---------|----------------|
| `.frm` (Forms) | Form Agent | WinForms with Designer | UI components, event handling |
| `.cls` (Classes) | Business Logic Agent | C# Classes | OOP patterns, encapsulation |
| `.bas` (Modules) | Business Logic Agent | Static Classes | Utility functions, shared code |
| Database Code | Data Access Agent | Entity Framework | ADODB → EF Core migration |

## ⚙️ Advanced Configuration

### Data Anonymization

Configure sensitive data anonymization in `Config/anonymizer_config.json`:

```json
{
  "patterns": [
    {
      "name": "email",
      "regex": "\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b",
      "replacement": "[EMAIL_REDACTED]"
    },
    {
      "name": "phone",
      "regex": "\\b\\d{3}[-.]?\\d{3}[-.]?\\d{4}\\b",
      "replacement": "[PHONE_REDACTED]"
    }
  ]
}
```

### Translation Rules

Customize translation behavior in `Config/translation_rules.json`:

```json
{
  "vb6_to_csharp": {
    "data_types": {
      "String": "string",
      "Integer": "int",
      "Long": "long"
    },
    "controls": {
      "CommandButton": "Button",
      "TextBox": "TextBox"
    }
  }
}
```

## 🧪 Testing and Validation

The pipeline includes comprehensive validation:

```bash
# Run all tests
python -m pytest Test/

# Run specific test categories
python -m pytest Test/test_core_analyzer.py
python -m pytest Test/test_translation_agents.py
python -m pytest Test/test_evaluation_framework.py

# Validate translated code
python Evaluation/evaluator.py MyTranslatedProject/
```

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** and add tests
4. **Run tests**: `python -m pytest`
5. **Commit changes**: `git commit -m 'Add amazing feature'`
6. **Push to branch**: `git push origin feature/amazing-feature`
7. **Open a Pull Request**

### Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/LegacyCodeToCSharp.git
cd LegacyCodeToCSharp

# Install development dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # If it exists

# Run tests
python -m pytest
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Getting Help

- **📖 Documentation**: Check the `/Documentation` folder for detailed guides
- **🐛 Issues**: [Create an issue](https://github.com/yourusername/LegacyCodeToCSharp/issues) for bugs
- **💡 Feature Requests**: [Open a discussion](https://github.com/yourusername/LegacyCodeToCSharp/discussions)
- **❓ Questions**: Use the Q&A section in discussions

### Troubleshooting

**Common Issues:**

1. **Translation fails**: Check that the VB6 project file (.vbp) is valid
2. **Missing dependencies**: Ensure all referenced VB6 files exist
3. **AI provider errors**: Verify your API keys or Ollama installation
4. **Build errors**: Check the generated C# code for syntax issues

## 🗺️ Roadmap

### Upcoming Features

- [ ] **WPF Support**: Translate VB6 forms to WPF applications
- [ ] **ASP.NET Core**: Web application translation capabilities  
- [ ] **Database Schema Migration**: Automatic database schema translation
- [ ] **Unit Test Generation**: Automated test generation for translated code
- [ ] **Visual Studio Extension**: IDE integration for seamless workflow
- [ ] **Performance Optimization**: Advanced optimization for translated code
- [ ] **Docker Support**: Containerized translation pipeline
- [ ] **CI/CD Integration**: GitHub Actions and Azure DevOps support

### Recent Updates

- ✅ Multi-agent translation system
- ✅ RAG-enhanced context retrieval
- ✅ Parallel processing support
- ✅ Comprehensive validation framework
- ✅ Entity Framework Core integration

---

<div align="center">

**⭐ Star this repository if you find it helpful!**

Made with ❤️ for legacy code modernization

</div>

